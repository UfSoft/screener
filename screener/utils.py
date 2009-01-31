# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from os import path
from genshi import Stream
from genshi.filters.html import HTMLFormFiller
from genshi.template import TemplateLoader
from werkzeug.wrappers import BaseRequest, BaseResponse, ETagRequestMixin
from werkzeug.local import Local, LocalManager
from werkzeug.utils import url_encode, url_quote

# calculate the path to the templates an create the template loader
TEMPLATE_PATH = path.join(path.dirname(__file__), 'templates')
template_loader = TemplateLoader(TEMPLATE_PATH, auto_reload=True,
                                 variable_lookup='lenient')

# context locals.  these two objects are use by the application to
# bind objects to the current context.  A context is defined as the
# current thread and the current greenlet if there is greenlet support.

local = Local()
local_manager = LocalManager([local])
request = local('request')
application = local('application')

def generate_template(template_name, **context):
    """Load and generate a template."""
    formfill = context.pop('formfill', None)
    context.update(
        url_for=url_for,
        shared_url=shared_url,
        format_datetime=format_datetime,
    )
    stream = template_loader.load(template_name).generate(**context)
    if formfill:
        return stream | HTMLFormFiller(data=formfill)
    return stream

def url_for(endpoint, **kwargs):
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

#===============================================================================
# Uploads Middleware
#===============================================================================
from os import makedirs, removedirs, remove
from shutil import move
from pprint import pprint
from uuid import uuid4
import simplejson
from werkzeug.utils import SharedDataMiddleware

class FileTooBig(Exception):
    """Exception raised when file is too big"""

class FileSizeOk(Exception):
    """p"""


class UploadsMiddleware(object):
    uploads = {}
    def __init__(self, app, uploads_folder, endpoint='/upload',
                 max_size=101024,
                 shared_path=path.join(path.dirname(__file__), 'shared')):

        shared_path = endpoint.rstrip('/') + '/static'
        self.app = SharedDataMiddleware(app, {
            endpoint.rstrip('/') + '/static': shared_path}
        )
        self.uploads_folder = uploads_folder
        self.endpoint = endpoint
        self.max_size = max_size



    def handle_get(self, request, environ, start_response):
        if 'stats' in request.values:
            print 'AJAX'
            uuid = request.values.get('stats')
            data = simplejson.dumps(self.uploads.get(uuid))
            if data:
                headers = [('Content-Type', 'text/javascript'),
                           ('Content-Length', str(len(data)))]
                print data, type(data)
                start_response('200 OK', headers)
                return [str(data)]
            return self.app(environ, start_response)
        data = """<form action="" method="post" enctype="multipart/form-data">
  <input type="file" name="uploaded_file">
  <input type="hidden" name="uuid" value="%s">
  <input type="submit" value="Submit">
</form>""" % uuid4().hex
        headers = [('Content-Type', 'text/html'),
                   ('Content-Length', str(len(data)))]
        start_response('200 OK', headers)
        return [data]

    def handle_post(self, request, environ, start_response):

        uuid = request.values.get('uuid')
        print uuid, request.files
        uploaded_file = request.files.get('uploaded_file')
#        thread.start_new_thread(self.handle_upload, (uploaded_file, uuid))

        data = str("""<html>
  <head>
    <script src="/shared/js/jquery.js" type="text/javascript"></script>
    <script src="/shared/js/jquery.blockUI.js" type="text/javascript"></script>
    <script src="/shared/js/screener.js" type="text/javascript"></script>
  </head>
  <body>
    <div id="output" style="display: none;">Uploaded 0 bytes of %s</div>
    <script type="text/javascript"/>
      uploads.info('/uploads', "#output", "%s", 1000);
    </script>
  </body>
</html>""" % (uploaded_file.filename, uuid))
#      jQuery.blockUI({message: $("#output"), css: {width: "600px"}});
#      function repetitive() {
#          jQuery.getJSON('/uploads?stats=%s', function(json) {
#            console.log(json);
#            if ( json.status == 2 ) {
#              jQuery.unblockUI();
#            } else {
#              $("#output").html("Uploaded " + json.size + " bytes of " + json.fname);
#              window.setTimeout("repetitive()", 1000);
#            };
#          });
#        };
#      window.setTimeout("repetitive()", 1000);
#    </script>
#  </body>
#</html>""" % (uploaded_file.filename, uuid))
        print data, type(data)
        headers = [('Content-Type', 'text/html'),
                   ('Content-Length', str(len(data)))]
        start_response('200 OK', headers)
        yield data
        import time
        print 'handling uploads'
        output_path = path.join(self.uploads_folder, uuid)
        makedirs(output_path)
        output_file_path = path.join(output_path, uploaded_file.filename)
        output_file = open(output_file_path, 'wb')
        self.uploads[uuid] = {
            'status': 0,
            'size': 0,
            'fname': uploaded_file.filename
        }
        try:
            self.uploads[uuid]['status'] = 1
            while 1:
                if output_file.tell() > self.max_size:
                    raise FileTooBig
                data = uploaded_file.read(1024)
                if not data:
                    raise FileSizeOk
                output_file.write(data)
                self.uploads[uuid]['size'] = output_file.tell()
                time.sleep(1)
        except FileTooBig:
            output_file.close()
            self.uploads[uuid]['status'] = -1
            self.uploads[uuid]['msg'] = "File is too big"
            remove(output_file_path)
            removedirs(output_path)
        except FileSizeOk:
            output_file.close()
            self.uploads[uuid]['status'] = 2
            move(output_file_path, self.uploads_folder)
            removedirs(output_path)
        raise StopIteration

    def __call__(self, environ, start_response):
        request = Request(environ)
        if not request.path.startswith(self.endpoint):
            return self.app(environ, start_response)

        if request.path == self.endpoint and request.method == 'GET':
            return self.handle_get(request, environ, start_response)
        if request.path == self.endpoint and request.method == 'POST':
            return self.handle_post(request, environ, start_response)
