# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ConfigParser import SafeConfigParser
from genshi.core import Stream
from os import path, makedirs
from screener.database import session
from screener.urls import url_map, handlers
from screener.utils import (Request, Response, local, local_manager,
    generate_template, ImageAbuseReported, ImageAbuseConfirmed, url_for,
    AdultContentException)
from screener.utils.crypto import gen_secret_key
from screener.utils.notification import NotificationSystem
from sqlalchemy import create_engine
from sqlalchemy.exceptions import InvalidRequestError
from time import time
from types import ModuleType
from werkzeug.exceptions import HTTPException, NotFound, Unauthorized
from werkzeug.utils import ClosingIterator, SharedDataMiddleware, redirect
import sys


#: path to shared data
SHARED_DATA = path.join(path.dirname(__file__), 'shared')

sys.modules['screener.config'] = config = ModuleType('config')

MESSAGE_404 = "The requested URL was not found on the server. If you entered" +\
              " the URL manually please check your spelling and try again."

class Screener(object):
    """Our central WSGI application."""

    def __init__(self, instance_folder):
        self.instance_folder = path.abspath(instance_folder)
        self.url_map = url_map
        self.init_screener()
        self.database_engine = create_engine(config.database_uri,
                                             echo=config.database_echo)

        # apply our middlewares.   we apply the middlewares *inside* the
        # application and not outside of it so that we never lose the
        # reference to the `Screener` object.
        self._dispatch = SharedDataMiddleware(self.dispatch_request, {
            '/shared':     SHARED_DATA
        })

        # free the context locals at the end of the request
        self._dispatch = local_manager.make_middleware(self._dispatch)

        # Attach the notification system
        self.notification = NotificationSystem(config.notification)

    def init_screener(self):
        if not path.exists(self.instance_folder):
            makedirs(path.join(self.instance_folder))
        parser = SafeConfigParser()

        config_file = path.join(self.instance_folder, 'screener.ini')
        if not path.isfile(config_file):
            parser.add_section('main')
            parser.set('main', 'database_uri', 'sqlite:///%(here)s/database.db')
            parser.set('main', 'database_echo', 'false')
            parser.set('main', 'uploads_path', '%(here)s/uploads')
            parser.set('main', 'max_size', '10485760') # 10 Mb
            parser.set('main', 'secret_key', gen_secret_key())
            parser.set('main', 'cookie_name', 'screener_cookie')
            parser.set('main', 'screener_domain', 'localhost')
            parser.set('main', 'host_country', '')
            parser.add_section('watermark')
            parser.set('watermark', 'optional', 'true')
            parser.set('watermark', 'font', '')
            parser.set('watermark', 'text', 'Screener')
            parser.add_section('notification')
            parser.set('notification', 'enabled', 'true')
            parser.set('notification', 'smtp_server', '')
            parser.set('notification', 'smtp_port', '25')
            parser.set('notification', 'smtp_user', '')
            parser.set('notification', 'smtp_pass', '')
            parser.set('notification', 'smtp_from', '')
            parser.set('notification', 'from_name', 'Screener')
            parser.set('notification', 'reply_to', '')
            parser.set('notification', 'use_tls', 'false')
            parser.write(open(config_file, 'w'))
        else:
            parser.readfp(open(config_file))
        parser.set('main', 'here', self.instance_folder)

        config.database_uri = parser.get('main', 'database_uri')
        config.database_echo = parser.getboolean('main', 'database_echo')
        config.uploads_path = path.abspath(parser.get('main', 'uploads_path'))
        config.max_size = parser.getint('main', 'max_size')
        config.secret_key = parser.get('main', 'secret_key', raw=True)
        config.cookie_name = parser.get('main', 'cookie_name')
        config.domain = parser.get('main', 'screener_domain')
        config.host_country = parser.get('main', 'host_country')
        if not config.host_country:
            import sys
            print "You need to configure 'host_country' on the config"
            print "That's required for the Terms of Service display"
            sys.exit()

        config.watermark = watermark = ModuleType('config.watermark')
        watermark.optional = parser.getboolean('watermark', 'optional')
        watermark.font = parser.get('watermark', 'font')
        watermark.text = parser.get('watermark', 'text')

        config.notification = notification = ModuleType('config.notification')
        notification.enabled = parser.getboolean('notification', 'enabled')
        notification.smtp_server = parser.get('notification', 'smtp_server')
        notification.smtp_port = parser.getint('notification', 'smtp_port')
        notification.smtp_user = parser.get('notification', 'smtp_user')
        notification.smtp_pass = parser.get('notification', 'smtp_pass')
        notification.smtp_from = parser.get('notification', 'smtp_from')
        notification.from_name = parser.get('notification', 'from_name')
        notification.reply_to =  parser.get('notification', 'reply_to')
        notification.use_tls = parser.getboolean('notification', 'use_tls')
        if not path.isdir(config.uploads_path):
            makedirs(config.uploads_path)
        self.config = config

    def setup_screener(self):
        """Called from the management script to generate the db."""
        from sys import exit
        from getpass import getpass
        from screener.database import DeclarativeBase, User

        DeclarativeBase.metadata.create_all(bind=self.database_engine)

        username = raw_input("Administrator Username [admin]: ")
        if not username:
            username = 'admin'

        while True:
            email = raw_input("Administrator Email Address: ")
            if email:
                break

        def ask_passwd(confirm=False):
            if confirm:
                prompt = "Password Confirm: "
            else:
                prompt = "Administrator Password: "
            while True:
                user_input = getpass(prompt)
                if user_input:
                    break
            return user_input

        passwd = ask_passwd()
        passwd_confirm = ask_passwd(True)
        if passwd != passwd_confirm:
            print "passwords do not match"
            exit(1)

        self.bind_to_context()
        session.add(User(username=username, email=email, confirmed=True,
                         passwd=passwd, is_admin=True))
        session.commit()

    def bind_to_context(self):
        """
        Useful for the shell.  Binds the application to the current active
        context.  It's automatically called by the shell command.
        """
        local.application = self

    def dispatch_request(self, environ, start_response):
        """Dispatch an incoming request."""
        # set up all the stuff we want to have for this request.  That is
        # creating a request object, propagating the application to the
        # current context and instanciating the database session.
        self.bind_to_context()
        request = Request(environ)
        request.config = config
        request.notification = self.notification
        request.bind_to_context()
        request.setup_cookie()

        self.url_adapter = url_map.bind_to_environ(
            environ, server_name=config.domain
        )

        try:
            endpoint, params = self.url_adapter.match()
            print 12345, endpoint, params
            request.endpoint = endpoint
            action = handlers[endpoint]
            response = action(request, **params)
            if isinstance(response, Stream):
                response = Response(response)

        except KeyError, e:
            print 'KeyError', e
            e.description = MESSAGE_404
            e.status = 404
            e.name = "Not Found"
            response = Response(generate_template('4xx.html', exception=e))
            response.status_code = 404
        except AdultContentException, e:
            request.session['redirect_to'] = endpoint
            request.session['redirect_params'] = params
            response = Response(generate_template('adult_content.html',
                                                  exception=e))
            response.status_code = e.code
        except (NotFound, ImageAbuseReported, ImageAbuseConfirmed), e:
            if e.code == 404:
                e.description = MESSAGE_404
            response = Response(generate_template('4xx.html', exception=e))
            response.status_code = e.code
            # Error Codes:
            #    404:    Not Found
            #    409:    Resource Conflict
            #    410:    Resource Gone
        except Unauthorized:
            response = redirect(url_for('account.login'))
        except HTTPException, e:
            response = e.get_response(environ)

        if request.session.should_save:
            if request.session.get('pmt'):
                max_age = 60 * 60 * 24 * 31
                expires = time() + max_age
            else:
                max_age = expires = None
            request.session.save_cookie(response, config.cookie_name,
                                        max_age=max_age, expires=expires,
                                        session_expires=expires)
        try:
            return ClosingIterator(response(environ, start_response),
                                   [local_manager.cleanup, session.remove])
        except InvalidRequestError:
            session.rollback()


    def __call__(self, environ, start_response):
        """Just forward a WSGI call to the first internal middleware."""
        return self._dispatch(environ, start_response)
