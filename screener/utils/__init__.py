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
from genshi.template import TemplateLoader
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

def generate_template(template_name, **context):
    """Load and generate a template."""
    formfill = context.pop('formfill', None)
    context.update(
        url_for=url_for,
        shared_url=shared_url,
        format_datetime=format_datetime,
        request=request
    )
    stream = template_loader.load(template_name).generate(**context)
    if formfill:
        return stream | HTMLFormFiller(data=formfill)
    return stream

def url_for(endpoint, *args, **kwargs):
    if hasattr(endpoint, '__url__'):
        return endpoint.__url__(*args, **kwargs)
    return application.url_adapter.build(endpoint, kwargs)

def shared_url(filename):
    """Returns a URL to a shared resource."""
    return url_for('shared', file=filename)

def format_datetime(obj):
    """Format a datetime object."""
    return obj.strftime('%Y-%m-%d %H:%M')

class Request(BaseRequest, ETagRequestMixin):
    """Simple request subclass that allows to bind the object to the
    current context.
    """
    def bind_to_context(self):
        local.request = self

    def setup_cookie(self):
        self.session = SecureCookie.load_cookie(
            self, application.config.cookie_name,
            application.config.secret_key.encode('utf-8')
        )

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

def template(template_name):
    """Templated response decorator"""
