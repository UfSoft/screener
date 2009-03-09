# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
from cStringIO import StringIO

from screener.database import session, Category, Image, User, or_
from screener.utils import url_for

def upload(request, image):
    image_data = StringIO(image.data)
    return {}

def add_category(request, name, description, private):
    if not name:
        return {'status': 1, 'msg': 'All arguments are needed'}
    category = Category.query.filter(or_(Category.name==name,
                                         Category.secret==name)).first()
    if category:
        return {'status': 1, 'name': category.name,
                'url': url_for(category, force_external=True),
                'msg': 'A category by this name already exists'}

    category = Category(name, description, private)
    session.add(category)
    session.commit()
    return {'status': 0, 'name': category.name,
            'url': url_for(category, force_external=True)}

def upload(request, image, category=None):
    """Upload an image"""
    if category:
        category = Category.query.filter(or_(Category.name==category,
                                             Category.secret==category)).first()
    if not category:
        Category(category_name, category_description, category_private)

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
        image = Image(image_path, mimetype,
                      description=request.values.get('description'),
                      private=private, submitter_ip=request.remote_addr)
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
