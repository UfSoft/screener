# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import sys
from ConfigParser import SafeConfigParser
from os import path, makedirs
from types import ModuleType
from sqlalchemy import create_engine
from werkzeug.utils import ClosingIterator, SharedDataMiddleware, redirect
from werkzeug.exceptions import HTTPException, NotFound

from screener.database import metadata, session
from screener.utils import (Request, Response, local, local_manager,
                            generate_template, url_for, UploadsMiddleware)
from screener.urls import url_map, handlers

#: path to shared data
SHARED_DATA = path.join(path.dirname(__file__), 'shared')

sys.modules['screener.config'] = config = ModuleType('config')

class Screener(object):
    """Our central WSGI application."""

    def __init__(self, instance_folder):
        self.instance_folder = path.abspath(instance_folder)
        self.url_map = url_map
        self.setup_screener()
        self.database_engine = create_engine(config.database_uri)

        # apply our middlewares.   we apply the middlewares *inside* the
        # application and not outside of it so that we never lose the
        # reference to the `Screener` object.
        self._dispatch = SharedDataMiddleware(self.dispatch_request, {
            '/shared':     SHARED_DATA,
            '/temp':       path.join(config.uploads_path, 'temp')
        })

        # free the context locals at the end of the request
        self._dispatch = local_manager.make_middleware(self._dispatch)
        self._uploads = UploadsMiddleware(self._dispatch,
                                          path.join(config.uploads_path, 'temp'),
                                          endpoint='/uploads')
        self._dispatch = local_manager.make_middleware(self._uploads)

    def setup_screener(self):
        if not path.exists(self.instance_folder):
            makedirs(path.join(self.instance_folder))
        parser = SafeConfigParser()

        config_file = path.join(self.instance_folder, 'screener.ini')
        if not path.isfile(config_file):
            parser.add_section('main')
            parser.set('main', 'database_uri', 'sqlite:///%(here)s/database.db')
            parser.set('main', 'uploads_path', '%(here)s/uploads')
            parser.set('main', 'max_size', '2048')
            parser.write(open(config_file, 'w'))
            parser.set('main', 'here', self.instance_folder)
        else:
            parser.readfp(open(config_file))
            parser.set('main', 'here', self.instance_folder)

        config.database_uri = parser.get('main', 'database_uri')
        config.uploads_path = path.abspath(parser.get('main', 'uploads_path'))
        config.max_size = parser.getint('main', 'max_size')

        if not path.isdir(config.uploads_path):
            makedirs(config.uploads_path)



    def init_database(self):
        """Called from the management script to generate the db."""
        metadata.create_all(bind=self.database_engine)

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
        request.bind_to_context()
        request.config = config

        self.url_adapter = url_map.bind_to_environ(environ)

        try:
            endpoint, params = self.url_adapter.match()
            action = handlers[endpoint]
            response = action(request, **params)
        except (KeyError, NotFound), e:
            response = Response(generate_template('404.html'))
            response.status_code = 404
        except HTTPException, e:
            response = e.get_response(environ)

        return ClosingIterator(response(environ, start_response),
                               session.remove)

    def __call__(self, environ, start_response):
        """Just forward a WSGI call to the first internal middleware."""
        return self._dispatch(environ, start_response)
