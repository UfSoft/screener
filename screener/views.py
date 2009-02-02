# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from PIL import Image
from os import remove
from os.path import join, splitext, isfile
from screener.utils import Response, generate_template
from tempfile import mktemp

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
                                              error="No file uploaded"))

        filename, ext = splitext(uploaded_file.filename)
        tempfile_path = mktemp()
        tempfile = open(tempfile_path, 'wb')
        while 1:
            if tempfile.tell() > request.config.max_size:
                tempfile.close()
                remove(tempfile_path)
                return Response(generate_template('upload.html',
                                                  error="File too big."))
            data = uploaded_file.read(2048)
            if not data:
                break
            tempfile.write(data)
        tempfile.close()

        try:
            image = Image.open(tempfile_path)
        except IOError:
            remove(tempfile_path)
            return Response(generate_template('upload.html',
                                              error="Invalid Image File"))

        try:
            image_path = join(request.config.uploads_path, filename)
            image.save(image_path+ext, ext[1:])
            image_width, image_height = image.size
            if image_width > 200 or image_height > 200:
                image.thumbnail((200, 200), Image.ANTIALIAS)
            image.save(image_path + '.thumbnail' + ext, ext[1:])
        except IOError:
            if isfile(image_path + ext):
                remove(image_path + ext)
            if isfile(image_path + '.thumbnail' + ext):
                remove(image_path + '.thumbnail' + ext)
            return Response(generate_template('upload.html',
                                              error="Failed to upload Image"))
        finally:
            remove(tempfile_path)

    return Response(generate_template('upload.html'))

