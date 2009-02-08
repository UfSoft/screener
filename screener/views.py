# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import PIL
from PIL import Image as PImage, ImageDraw, ImageFont
from os import remove, makedirs, removedirs, symlink, fstat, getcwd, chdir
from os.path import join, splitext, isfile, isdir, dirname, basename
from screener.utils import generate_template
from tempfile import mktemp
from math import atan, degrees
from screener.database import session, Category, Image, and_, or_
from screener.utils import (url_for, Response, ImageAbuseReported,
                            ImageAbuseConfirmed)

from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect
from werkzeug.http import parse_etags, remove_entity_headers
from mimetypes import guess_type

from stat import ST_SIZE, ST_MTIME
from time import asctime, gmtime, time
from datetime import timedelta


def categories_list(request):
    categories = Category.query.filter(
        or_(Category.private==False,
            Category.secret.in_(request.session.get('secrets', [])))
    ).all()
    return generate_template('category_list.html', categories=categories)


def category_list(request, category=None):
    if not category:
        raise NotFound("Category not found.")
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()
    if category is None:
        raise NotFound("Category not found.")
    return generate_template('category.html', category=category)


def index(request):
    return generate_template('index.html')


def upload(request, category=None):
    if category:
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
        category = Category.query.get(category_name)
        if not category:
            category_description = request.values.get('category_description')
            category_private = request.values.get('category_private') == 'yes'
            category = Category(category_name, category_description,
                                category_private)
            if category_private:
                request.session.setdefault('secrets',
                                           []).append(category.secret)


        if Image.query.filter(and_(Image.filename==uploaded_file.filename,
                                   Image.category==category)).first():
            return generate_template(
                'upload.html', error="Image already exists for this category",
                formfill=request.values, category=category)

        category_path = join(request.config.uploads_path, category.name)
        if not isdir(category_path):
            makedirs(category_path)

        current_cwd = getcwd()

        filename, ext = splitext(uploaded_file.filename)
        extension = ext[1:]
        if extension.lower() == 'jpg':
            extension = 'jpeg'
            ext = '.jpeg'
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
            watermark_text = request.values.get('watermark_text')
            watermark_font = request.config.watermark_font
            if watermark_font and watermark_text:
                original = image.convert("RGBA")
                original_width, original_height = original.size
                watermark = PImage.new("RGBA", original.size)
                draw = ImageDraw.ImageDraw(watermark, "RGBA")
                size = 0
                while True:
                    size += 1
                    nextfont = ImageFont.truetype(watermark_font, size)
                    nxttxtwidth, nxttxtheight = nextfont.getsize(watermark_text)
                    if nxttxtwidth + nxttxtheight / 3 > watermark.size[0]:
                        break
                    font = nextfont
                    textwidth, textheight = nxttxtwidth, nxttxtheight
                draw.setfont(font)
                draw.text(((watermark.size[0]-textwidth)/2,
                           (watermark.size[1]-textheight)/2), watermark_text)
                watermark = watermark.rotate(
                    degrees(atan(float(original_height)/original_width)),
                    PImage.BICUBIC
                )
                mask = watermark.convert("L").point(lambda x: min(x, 55))
                watermark.putalpha(mask)
                original.paste(watermark, None, watermark)
                original.save(image_path, extension)
            else:
                image.save(image_path, extension)

            # Resized version
            resized_path = join(category_path, filename + '.resized' + ext)
            if image_width > 1100:
                if watermark_font and watermark_text:
                    original.thumbnail((1100, 1100), PImage.ANTIALIAS)
                    original.save(resized_path, extension)
                else:
                    image.thumbnail((1100, 1100), PImage.ANTIALIAS)
                    image.save(resized_path, extension)
            else:
                chdir(dirname(image_path))
                symlink(basename(image_path), basename(resized_path))

            # Thumbnailed Version
            thumbnail_path = join(category_path, filename + '.thumbnail' + ext)
            if image_width > 200 or image_height > 200:
                image.thumbnail((200, 200), PImage.ANTIALIAS)
                image.save(thumbnail_path, extension)
            else:
                chdir(dirname(image_path))
                symlink(basename(image_path), basename(thumbnail_path))

            if getcwd() != current_cwd:
                # Changed directories for symlink'ing, back to old CWD
                chdir(current_cwd)
        except IOError:
            for path in (image_path, resized_path, thumbnail_path):
                if isfile(path):
                    remove(path)
            if getcwd() != current_cwd:
                # Changed directories for symlink'ing, back to old CWD
                chdir(current_cwd)
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
        private = request.values.get('private') == 'yes'
        image = Image(image_path, mimetype, description, private,
                      request.remote_addr)
        image.category = category
        session.add(image)
        session.commit()
        if private:
            request.session.setdefault('flashes', []).append(
                "Your hidden image can be found <a href=\"%s\">here</a>"
                % url_for(image, 'image'))
            request.session.setdefault('secrets', []).append(image.id)
        if request.values.get('multiple'):
            return redirect(
                url_for('upload', category=category.private and category.secret
                                           or category.name), 303)
        else:
            return redirect(url_for(category), 303)

    return generate_template(
        'upload.html', category=category,
        watermark_text=request.config.watermark_text,
        watermark_optional=request.config.watermark_optional)


def show_image(request, category=None, image=None):
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()
    filename, extension = splitext(image)
    if not extension:
        image = Image.query.get(image)
    else:
        image = Image.query.filter(
            and_(Image.filename.in_([filename+extension,
                                     filename[:-len('.thumbnail')]+extension,
                                     filename[:-len('.resized')]+extension]),
                 Image.category==category)).first()
    if not image:
        raise NotFound("Requested image was not found")
    if image.abuse_status == 1:
        raise ImageAbuseReported
    elif image.abuse_status == 2:
        raise ImageAbuseConfirmed
    return generate_template('image.html', image=image)

def serve_image(request, category=None, image=None):
    print 'should have served image?', image, type(image), request.endpoint, category
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()

    filename, extension = splitext(image)
    if not extension:
        loaded = Image.query.get(image)
    else:
        loaded = Image.query.filter(
            or_(and_(Image.filename==filename+extension,
                     Image.category==category),
                and_(Image.filename==filename[:-len('.thumbnail')]+extension,
                     Image.category==category),
                and_(Image.filename==filename[:-len('.resized')]+extension,
                     Image.category==category))).first()
    if not loaded:
        raise NotFound("Requested image was not found")

    if loaded.abuse_status == 1:
        raise ImageAbuseReported
    elif loaded.abuse_status == 2:
        raise ImageAbuseConfirmed

    content_type = loaded.mimetype
    picture = open(getattr(loaded, "%s_path" % request.endpoint), 'rb')

    size = fstat(picture.fileno())[ST_SIZE]
    # This image won't change, allow caching it for a year
    expiry = loaded.stamp + timedelta(days=365)

    headers = [
        # If the image is private, don't allow cache systems to cache it
        # only the requesting user can cache it
        ('Cache-Control', loaded.private and 'private' or 'public'),
        # The rest of the headers
        ('Content-Length', str(size)),
        ('Expires', expiry.strftime("%a %b %d %H:%M:%S %Y")),
        ('ETag', loaded.etag)
    ]
    if request.if_none_match.contains(loaded.etag):
        remove_entity_headers(headers)
        return Response('', 304, headers=headers)

    def stream():
        while True:
            data = picture.read(2048)
            if not data:
                break
            yield data

    return Response(stream(), content_type=content_type, headers=headers)


def report_abuse(request, category=None, image=None):
    return generate_template('report_abuse.html')
