# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from PIL import Image as PImage
from os import remove, makedirs, removedirs, link, fstat
from os.path import join, splitext, isfile, isdir
from screener.utils import generate_template
from tempfile import mktemp

from screener.database import session, Category, Image, and_, or_
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
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()
    return generate_template('category.html', category=category)

def invalid(request):
    return generate_template('index.html')

def index(request):
    return generate_template('index.html')


def upload(request, category=None):
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()
    if request.method == 'POST':
        uploaded_file = request.files['uploaded_file']
        if not uploaded_file:
            return generate_template('upload.html', error="No file uploaded",
                                     formfill=request.values,
                                     category=category)
        category_name = request.values.get('category_name', 'uncategorized')
        if len(category_name.split()) > 1:
            return generate_template(
                'upload.html', error="Category names cannot contain spaces",
                formfill=request.values, category=category)
        category = session.query(Category).get(category_name)
        if not category:
            category_description = request.values.get('category_description')
            category_private = request.values.get('category_private') == 'yes'
            category = Category(category_name, category_description,
                                category_private)
            session.add(category)

        category_path = join(request.config.uploads_path, category.name)
        if not isdir(category_path):
            makedirs(category_path)

        filename, ext = splitext(uploaded_file.filename)
        extension = ext[1:]
        mimetype, _ = guess_type(uploaded_file.filename)

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
            image_width, image_height = image.size

            image_path = join(category_path, filename + ext)
            # Original Image
            image.save(image_path, extension)

            # Resized version
            resized_path = join(category_path, filename + '.resized' + ext)
            if image_width > 1100:
                image.thumbnail((1100, 1100), PImage.ANTIALIAS)
                image.save(resized_path, extension)
            else:
                link(image_path, resized_path)

            # Thumbnailed Version
            thumbnail_path = join(category_path, filename + '.thumbnail' + ext)
            if image_width > 200 or image_height > 200:
                image.thumbnail((200, 200), PImage.ANTIALIAS)
                image.save(thumbnail_path, extension)
            else:
                link(image_path, thumbnail_path)
        except IOError:
            for path in (image_path, resized_path, thumbnail_path):
                if isfile(path):
                    remove(path)
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
        image = Image(image_path, mimetype, description, secret)
        image.category = category
        session.commit()
        if request.values.get('multiple'):
            return redirect(
                url_for('upload', category=category.private and category.secret
                                           or category.name), 303)
        else:
            return redirect(url_for(category), 303)

    return generate_template('upload.html', category=category)

def show_image(request, image=None):
    filename, extension = splitext(image)
#    print 'show image', image, filename, extension
    if not extension:
        image = Image.query.filter(Image.secret==image).first()
    else:
        image = Image.query.filter(
            or_(Image.filename==filename+extension,
                Image.filename==filename[:-len('.thumbnail')]+extension,
                Image.filename==filename[:-len('.resized')]+extension)).first()
    if not image:
        raise NotFound("Requested image was not found")
    return generate_template('image.html', image=image)

def serve_image(request, image=None):
    print 'should have served image?', image, type(image), request.endpoint

    filename, extension = splitext(image)
    if not extension:
        loaded = Image.query.filter(Image.secret==image).first()
    else:
        loaded = Image.query.filter(
            or_(Image.filename==filename+extension,
                Image.filename==filename[:-len('.thumbnail')]+extension,
                Image.filename==filename[:-len('.resized')]+extension)).first()
    if not loaded:
        raise NotFound("Image not found")

    content_type = loaded.mimetype
    picture = open(getattr(loaded, "%s_path" % request.endpoint), 'rb')

    size = fstat(picture.fileno())[ST_SIZE]
    expiry = loaded.stamp.strftime("%a %b %d %H:%M:%S %Y")

    headers = [
        ('Cache-Control', 'public'),
        ('Content-Length', str(size)),
        ('Expires', expiry),
        ('ETag', loaded.etag)
    ]
#    print 'HEADERS', headers, request.headers.get('HTTP_IF_NONE_MATCH')
    if parse_etags(request.headers.get('HTTP_IF_NONE_MATCH')) \
                                                    .contains(loaded.etag):
        remove_entity_headers(headers)
        return Response('', 304, headers=headers)

#    print type(request.headers)
    return Response(picture.read(), content_type=content_type, headers=headers)
