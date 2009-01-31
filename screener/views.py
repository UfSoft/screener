# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from genshi.builder import tag
from werkzeug.exceptions import NotFound
from werkzeug.utils import html
from screener.utils import Response, generate_template, url_for

class FileSizeOk(Exception):
    """Exception raised in case file is not bigger then allowed"""

class FileSizeTooBig(Exception):
    """Exception raised in case file is bigger then allowed"""

def categories(request, category=None):
    pass

def invalid(request, **kw):
    return Response(generate_template('index.html'))

def index(request, **kw):
    return Response(generate_template('index.html'))

def upload(request):
    context = {'max_size': request.config.max_size}
    if request.method == 'POST':
        print 333, request.values
        print 333, request.files
        f = request.files['Filedata']
        f.save('/tmp/upload-%s' % f.filename)
        return Response('ok')
        return Response(f.filename, 200, content_type=f.content_type)
#        if not 'uploaded_file' in request.files:
#            context.update(error="No file uploaded", formfill=request.values)
#            Response(generate_template('upload.html', **context))
#        f = request.files['uploaded_file']
#        print f.content_length
#        print f.content_type
#
#        def stream_upload():
#            print 'uploading, max =', request.config.max_size
#            uploaded_size = 0
#            while 1: #uploaded_size <= request.config.max_size:
#                print uploaded_size, request.config.max_size
#                if uploaded_size <= request.config.max_size:
#                    raise FileSizeTooBig
#                uploaded_size += 1024
#                data = f.read(1024)
#                if not data:
#                    break
#                yield data
#        try:
#            uploaded_file = list(stream_upload())
#        except FileSizeTooBig:
#            print 'too big raised'
#            context.update(error="File Size Too Big", formfill=request.values)
#            return Response(generate_template('upload.html', **context))

    return Response(generate_template('upload.html', **context))

def hidden_upload1(request):
    import simplejson, os
    from uuid import uuid4
    if not request.method == 'POST':
        print 'not post'
        raise NotFound()

    print request.files
    uuid = uuid4().hex
    f = request.files['userfile']
    def stream():
        current_size = 0
        while 1:
            try:
                if current_size > request.config.max_size:
                    raise FileSizeTooBig
                current_size += 2048
                data = f.read(2048)
                if not data:
                    raise FileSizeOk
            except FileSizeTooBig:
                return Response("File Too Big")
            except FileSizeOk:
                f.save(os.path.join(request.config.uploads_path, 'temp', uuid))
                response = {
                    'uuid': uuid,
                    'fname': f.filename
                }
                Response(simplejson.dumps(response),
                         200, content_type='application/json')
    f.save(os.path.join(request.config.uploads_path, 'temp', uuid))
    response = """
<img src="%s"/>
<input type="hidden" name="file" value="%s"/>
""" % (url_for('temp', file=uuid) % uuid)
    return Response(response)
    return Response(stream(), 200, content_type=f.content_type)

def hidden_upload(request):
    from PIL import Image
    import ImageFile
    import simplejson, os
    from uuid import uuid4
    uuid = uuid4().hex
    if not request.method == 'POST': # or 'uploaded_file' not in request.values:
        print 'not post'
        raise NotFound()

    print request.values

    parser = ImageFile.Parser()
    while 1:
        f = request.files['uploaded_file']
        data = f.read(1024)
        if not data:
            break
        parser.feed(data)

    try:
        image = parser.close()
        if not image:
            return Response("No image uploaded")
        image_path = os.path.join(request.config.uploads_path, 'temp', uuid)
        print 'image path', image_path, image_path+'.png'
        image.save(image_path+'.png')
        print os.path.isfile(image_path+'.png')
        image.thumbnail((200, 200), Image.ANTIALIAS)
        image.save(image_path+'.thumbnail.png')

        return Response(
            html.img(src=url_for('temp', file=uuid+'.thumbnail.png')) +
            html.input(type='hidden', name='uuid', value=uuid)
        )
    except IOError, err:
        return Response("Failed to upload Image")


