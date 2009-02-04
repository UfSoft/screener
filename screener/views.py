# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from PIL import Image as PImage
from os import remove, makedirs, removedirs
from os.path import join, splitext, isfile, isdir
from screener.utils import generate_template
from tempfile import mktemp

from screener.database import session
from screener.models import Category, Image
from screener.utils import url_for, Response

from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect
from werkzeug.http import parse_etags, remove_entity_headers
from mimetypes import guess_type

from stat import ST_SIZE, ST_MTIME
from time import asctime, gmtime, time

def categories_list(request):
    categories = Category.query.filter(Category.private==False).all()
    return generate_template('category_list.html', categories=categories)

def category_list(request, category=None):
    if not category:
        raise NotFound()
    return generate_template('category.html', category=category)

def invalid(request):
    return generate_template('index.html')

def index(request):
    return generate_template('index.html')


def upload(request, category=None):
    if category:
        print category.name
        print category.secret

    if request.method == 'POST':
        uploaded_file = request.files['uploaded_file']
        if not uploaded_file:
            return generate_template('upload.html', error="No file uploaded",
                                     formfill=request.values,
                                     category=category)
        category_name = request.values.get('category_name', 'uncategorized')
        if len(category_name.split()) > 1:
            print category_name, category_name.split()
            return generate_template(
                'upload.html', error="Category names cannot contain spaces",
                formfill=request.values, category=category)
        category = session.query(Category).get(category_name)
        if not category:
            category_description = request.values.get('category_description')
            category_private = request.values.get('category_private') == 'yes'
            print category_name, category_description, category_private
            category = Category(category_name, category_description,
                                category_private)
            session.add(category)

        category_path = join(request.config.uploads_path, category.name)
        if not isdir(category_path):
            makedirs(category_path)

        filename, ext = splitext(uploaded_file.filename)
        tempfile_path = mktemp()
        tempfile = open(tempfile_path, 'wb')
        while 1:
            if tempfile.tell() > request.config.max_size:
                tempfile.close()
                remove(tempfile_path)
                return generate_template('upload.html', error="File too big.",
                                         formfill=request.values,
                                         category=category)
            data = uploaded_file.read(2048)
            if not data:
                break
            tempfile.write(data)
        tempfile.close()

        try:
            image = PImage.open(tempfile_path)
        except IOError:
            remove(tempfile_path)
            return generate_template('upload.html', error="Invalid Image File",
                                     formfill=request.values,
                                     category=category)

        try:
            image_path = join(category_path, filename + ext)
            image_width, image_height = image.size
            image.save(image_path, ext[1:])
            resized_path = join(category_path, filename+ '.resized' + ext)
            if image_width > 800:
                image.thumbnail((800, 800), PImage.ANTIALIAS)
            image.save(resized_path, ext[1:])
            image.save(image_path, ext[1:])
            if image_width > 200 or image_height > 200:
                image.thumbnail((200, 200), PImage.ANTIALIAS)
            thumb_path = join(category_path, filename+ '.thumbnail' + ext)
            image.save(thumb_path, ext[1:])
        except IOError:
            if isfile(image_path):
                remove(image_path)
            if isfile(thumb_path):
                remove(thumb_path)
            try:
                removedirs(category_path)
            except OSError:
                # Directory not empty
                pass
            return generate_template('upload.html', error="Failed Save Image",
                                     formfill=request.values,
                                     category=category)
        finally:
            remove(tempfile_path)

        description = request.values.get('description')
        secret = request.values.get('secret')
        dbimage = Image(image_path, description, secret)
        dbimage.category = category
        session.commit()
        if request.values.get('multiple'):
            if category.private:
                return redirect(url_for('upload', secret=category.secret), 303)
            else:
                return redirect(url_for('upload', category=category.name), 303)
        elif category.private:
            return redirect(url_for('category', secret=category.secret), 303)
        else:
            return redirect(url_for('category', category=category.name), 303)


    return generate_template('upload.html', category=category)

def show_image(request, image=None):
    return generate_template('image.html', image=image)

def serve_image(request, image=None):
    print 'should have served image?', image

    if request.endpoint == 'thumbs':
        content_type, content_encoding = guess_type(image.thumbpath)
        print content_type, content_encoding
        import os
        print os.stat(image.thumbpath)
        imgfd = open(image.thumbpath, 'rb')
        fstat = os.fstat(imgfd.fileno())
        size = fstat[ST_SIZE]
        mtime = fstat[ST_MTIME]
        expiry = asctime(gmtime(time() + 3600))

        headers = [
            ('Cache-Control', 'public'),
            ('Content-Length', str(size)),
            ('Expires', expiry),
            ('ETag', image.etag)
        ]
        print 'HEADERS', headers, request.headers.get('HTTP_IF_NONE_MATCH')
        if parse_etags(request.headers.get('HTTP_IF_NONE_MATCH')) \
                                                        .contains(image.etag):
            remove_entity_headers(headers)
            return Response('', 304, headers=headers)

        print type(request.headers)

        data = imgfd.read()

    elif request.endpoint == 'images':
        content_type, content_encoding = guess_type(image.filepath)
        print content_type, content_encoding
        import os
        print os.stat(image.filepath)
        imgfd = open(image.filepath, 'rb')
        fstat = os.fstat(imgfd.fileno())
        size = fstat[ST_SIZE]
        mtime = fstat[ST_MTIME]
        expiry = asctime(gmtime(time() + 3600))

        headers = [
            ('Cache-Control', 'public'),
            ('Content-Length', str(size)),
            ('Expires', expiry),
            ('ETag', image.etag)
        ]
        print 'HEADERS', headers, request.headers.get('HTTP_IF_NONE_MATCH')
        print 1, request.if_match
        print 2, request.if_none_match, type(request.if_none_match)
        print 3, request.cache_control, type(request.cache_control)
        print 4, request.if_modified_since
        if request.if_none_match.contains(image.etag):
            remove_entity_headers(headers)
            return Response('', 304, headers=headers)

        print type(request.headers)

        data = imgfd.read()
    else:
        raise NotFound

    return Response(data, content_type=content_type, headers=headers)

def serve_thumbs(request, image=None):
    print 'should have served thumb?', image
    if request.endpoint == 'thumbs':
        content_type, content_encoding = guess_type(image.thumbpath)
        data = open(image.thumbpath, 'rb').read()
    elif request.endpoint == 'images':
        content_type, content_encoding = guess_type(image.filepath)
        data = open(image.filepath, 'rb').read()
    else:
        raise NotFound

    return Response(data, content_type=content_type)
