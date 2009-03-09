# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from PIL import Image as PImage, ImageDraw, ImageFont
from datetime import timedelta
from math import atan, degrees
from mimetypes import guess_type
from os import remove, makedirs, removedirs, symlink, getcwd, chdir
from os.path import join, splitext, isfile, isdir, dirname, basename, getsize
from screener.database import session, User, Category, Image, Abuse, and_, or_
from screener.utils import (url_for, Response, ImageAbuseReported, flash,
                            ImageAbuseConfirmed, generate_template,
                            AdultContentException)
from tempfile import mktemp
from werkzeug.exceptions import NotFound
from werkzeug.http import remove_entity_headers
from werkzeug.utils import redirect




def categories_list(request):
    """Return the available list of categories"""
    return generate_template('category_list.html',
                             categories=Category.visible())


def category_list(request, category=None):
    """Return the available list of images under a specific category"""
    if not category:
        raise NotFound("Category not found.")
    category = Category.query.filter(or_(Category.name==category,
                                         Category.secret==category)).first()
    if category is None:
        raise NotFound("Category not found.")
    return generate_template('category.html', category=category)


def upload(request, category=None):
    """Upload an image"""
    if category:
        category = Category.query.filter(or_(Category.name==category,
                                             Category.secret==category)).first()
    if request.method == 'POST':
        agree_to_tos = request.values.get('tos') == 'yes'
        if not request.user.confirmed and not agree_to_tos:
            error = 'You must agree to the <a href="%s">Terms of Service</a>.'
            return generate_template( 'upload.html',
                                      error=error % url_for('tos'),
                                      formfill=request.values,
                                      category=category)
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
            watermark_font = request.config.watermark.font
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
        except OSError, error:
            return generate_template('upload.html',
                error="File already exists. Submitted the form twice?",
                formfill=request.values,
                category=category)
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

        private = request.values.get('private') == 'yes'
        adult_content = request.values.get('adult_content') == 'yes'
        image = Image(image_path, mimetype,
                      description=request.values.get('description'),
                      private=private, submitter_ip=request.remote_addr,
                      adult_content=adult_content)
        image.category = category
        session.add(image)
        session.commit()
        # :\   Double Commit!?
        image.owner.update_disk_usage()
        session.commit()
        if private:
            flash("Your hidden image can be found <a href=\"%s\">here</a>" %
                  url_for(image, 'show'))
        if request.values.get('multiple'):
            return redirect(
                url_for('upload', category=category.private and category.secret
                                           or category.name), 303)
        else:
            return redirect(url_for(category), 303)

    return generate_template(
        'upload.html', category=category,
        watermark_text=request.config.watermark.text,
        watermark_optional=request.config.watermark.optional)


def show_image(request, category=None, image=None):
    """Show the resized version of an image"""
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

    if image.abuse and image.abuse.confirmed:
        raise ImageAbuseConfirmed
    elif image.abuse:
        raise ImageAbuseReported
    if image.adult_content and not request.user.show_adult_content:
        raise AdultContentException

    image.views += 1
    session.commit()

    return generate_template('image.html', image=image)

def serve_image(request, leecher=None, category=None, image=None):
    """Serve the images"""

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

    if not request.user.is_admin:
        if loaded.abuse and loaded.abuse.confirmed:
            raise ImageAbuseConfirmed
        elif loaded.abuse:
            raise ImageAbuseReported
    if not request.user.show_adult_content and loaded.adult_content:
        raise AdultContentException

    content_type = loaded.mimetype
    picture_path = getattr(loaded, "%s_path" % request.endpoint)
    picture = open(picture_path, 'rb')

    size = getsize(picture_path)
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
        try:
            while True:
                data = picture.read(2048)
                if not data:
                    break
                yield data
        finally:
            picture.close()

    return Response(stream(), content_type=content_type, headers=headers)


def report_abuse(request, category=None, image=None):
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

    if image.abuse:
        flash("An abuse report for this image already exists")
        return redirect(url_for('index'))

    if request.method == 'POST':
        reason = request.values.get('reason')
        reporter_ip = request.remote_addr
        reporter_email = request.values.get('email')
        if not reason or not reporter_email:
            return generate_template('abuse.html', category=category,
                image=image, error="You need both your email address and a "
                                   "reason why you're reporting this abuse.")

        abuse = Abuse(image, reason, reporter_ip, reporter_email)
        session.add(abuse)

        request.notification.sendmail("Image Abuse Report Confirmation",
                                      'abuse.txt', {'report': abuse},
                                      reporter_email)

        image.owner.update_disk_usage()
        session.commit()
    return generate_template('abuse.html', category=category, image=image)


def report_abuse_confirm(request, hash=None):
    hash = request.values.get('confirm_hash', hash)
    if not hash:
        flash("Please insert the hash you were given")
        return generate_template('abuse_confirm.html')
    else:
        report = Abuse.query.get(hash)
        if not report:
            flash("There is no report to confirm on the URL you used")
            return redirect(url_for('index'))
        elif report and report.confirmed:
            flash("The abuse report was already confirmed")
            return redirect(url_for('index'))
        report.confirmed = True
        session.commit()
        flash("The abuse report is now confirmed")
        return redirect(url_for('index'))
    return generate_template('abuse_confirm.html')

def tos(request):
    return generate_template('tos.html')
