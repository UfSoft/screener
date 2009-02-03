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
from screener.utils import Response, generate_template
from tempfile import mktemp

from screener.database import session
from screener.models import Category, Image

def categories(request, category=None):
    pass

def invalid(request):
    return Response(generate_template('index.html'))

def index(request):
    return Response(generate_template('index.html'))


def upload(request):

    if request.method == 'POST':
        uploaded_file = request.files['uploaded_file']
        if not uploaded_file:
            return Response(generate_template('upload.html',
                                              error="No file uploaded",
                                              formfill=request.values))
        category_name = request.values.get('category_name', 'uncategorized')
        if len(category_name.split()) > 1:
            print category_name, category_name.split()
            return Response(generate_template('upload.html',
                error="Category names cannot contain spaces",
                formfill=request.values))
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
                return Response(generate_template('upload.html',
                                                  error="File too big.",
                                                  formfill=request.values))
            data = uploaded_file.read(2048)
            if not data:
                break
            tempfile.write(data)
        tempfile.close()

        try:
            image = PImage.open(tempfile_path)
        except IOError:
            remove(tempfile_path)
            return Response(generate_template('upload.html',
                                              error="Invalid Image File",
                                              formfill=request.values))

        try:
            image_path = join(category_path, filename + ext)
            image.save(image_path, ext[1:])
            image_width, image_height = image.size
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
            return Response(generate_template('upload.html',
                                              error="Failed Save Image",
                                              formfill=request.values))
        finally:
            remove(tempfile_path)

        description = request.values.get('description')
        secret = request.values.get('secret')
        dbimage = Image(image_path, description, secret)
        dbimage.category = category
        session.commit()

    return Response(generate_template('upload.html'))

