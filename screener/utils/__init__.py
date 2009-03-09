# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
import screener
from os import path
from genshi import Stream
from genshi.filters.html import HTMLFormFiller
from genshi.template import TemplateLoader, MarkupTemplate, NewTextTemplate
from werkzeug.wrappers import BaseRequest, BaseResponse, ETagRequestMixin
from werkzeug.local import Local, LocalManager
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.exceptions import NotFound


__all__ = ['local', 'local_manager', 'request', 'application',
           'generate_template', 'url_for', 'shared_url', 'format_datetime',
           'Request', 'Response']

# calculate the path to the templates an create the template loader
TEMPLATE_PATH = path.join(path.dirname(screener.__file__), 'templates')
template_loader = TemplateLoader(TEMPLATE_PATH, auto_reload=True,
                                 variable_lookup='lenient')

# context locals.  these two objects are use by the application to
# bind objects to the current context.  A context is defined as the
# current thread and the current greenlet if there is greenlet support.

local = Local()
local_manager = LocalManager([local])
request = local('request')
application = local('application')

class ImageAbuseReported(NotFound):
    description = "Abuse Reported."
    code = 409

class ImageAbuseConfirmed(NotFound):
    description = "Abuse Reported. Image Removed."
    code = 410

class AdultContentException(ImageAbuseReported):
    description = "STOP. Adult Content."

def generate_template(template_name, **context):
    """Load and generate a template."""
    formfill = context.pop('formfill', None)
    context.update(
        url_for=url_for,
        shared_url=shared_url,
        format_datetime=format_datetime,
        pretty_size=pretty_size,
        request=request
    )
    if template_name.endswith('.txt'):
        cls = NewTextTemplate
    else:
        cls = MarkupTemplate
    stream = template_loader.load(template_name, cls=cls).generate(**context)
    if formfill:
        return stream | HTMLFormFiller(data=formfill)
    return stream

def url_for(endpoint, *args, **kwargs):
    if hasattr(endpoint, '__url__'):
        return endpoint.__url__(*args, **kwargs)
    if 'force_external' in kwargs:
        force_external = kwargs.pop('force_external')
    else:
        force_external = False
    return application.url_adapter.build(endpoint, kwargs,
                                         force_external=force_external)

def shared_url(filename):
    """Returns a URL to a shared resource."""
    return url_for('shared', file=filename)

def format_datetime(obj):
    """Format a datetime object."""
    return obj.strftime('%Y-%m-%d %H:%M:%S')

def pretty_size(size, format='%.1f'):
    if not size:
        return '0 bytes'
    jump = 512
    if size < jump:
        return '%d bytes' % size
    units = ['KB', 'MB', 'GB', 'TB']
    i = 0
    while size >= jump and i < len(units):
        i += 1
        size /= 1024.
    return (format + ' %s') % (size, units[i - 1])

def flash(message, error=False):
    request.session.setdefault(error and 'errors' or 'flashes',
                               []).append(message)

class Request(BaseRequest, ETagRequestMixin):
    """Simple request subclass that allows to bind the object to the
    current context.
    """
    def bind_to_context(self):
        local.request = self

    def login(self, user, permanent=False):
        self.user = user
        self.session['uuid'] = user.uuid
        self.session['lv'] = user.last_visit
        if permanent:
            self.session['pmt'] = permanent

    def logout(self):
        self.session.clear()

    def setup_cookie(self):
        from screener.database import User, session
        self.session = SecureCookie.load_cookie(
            self, application.config.cookie_name,
            application.config.secret_key.encode('utf-8')
        )

        def new_user():
            user = User()
            session.add(user)
            return user

        if 'uuid' not in self.session:
            self.login(new_user(), permanent=True)
            self.session.setdefault('flashes', []).append(
                "A unique cookie has been sent to your browser that "
                "enables you to see your private images when browsing the "
                "categories.<br>Otherwise, you can only access them by "
                "their direct URL.")
        else:
            user = User.query.get(self.session.get('uuid'))
            if not user:
                self.login(new_user(), permanent=True)
                self.session.setdefault('flashes', []).append(
                    "A unique cookie has been sent to your browser that "
                    "enables you to see your private images when browsing the "
                    "categories.<br>Otherwise, you can only access them by "
                    "their direct URL.")
            else:
                self.login(user)
        self.user.update_last_visit()
        session.commit()

class Response(BaseResponse):
    """
    Encapsulates a WSGI response.  Unlike the default response object werkzeug
    provides, this accepts a genshi stream and will automatically render it
    to html.  This makes it possible to switch to xhtml or html5 easily.
    """

    default_mimetype = 'text/html'

    def __init__(self, response=None, status=200, headers=None, mimetype=None,
                 content_type=None):
        if isinstance(response, Stream):
            response = response.render('html', encoding=None, doctype='html')
        BaseResponse.__init__(self, response, status, headers, mimetype,
                              content_type)
