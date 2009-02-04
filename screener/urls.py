# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import re
from werkzeug.exceptions import NotFound
from werkzeug.routing import Map, Rule, BaseConverter, ValidationError
from screener import views, database, models
from screener.models import Category, Image


class CategoryConverter(BaseConverter):
    secure = False
    regex = '[^/]{1,39}'

    def to_python(self, value):
        if self.secure:
            instance = Category.query.filter(Category.secret==value).first()
        else:
            instance = Category.query.get(value)
        if not instance or (instance and instance.private and not self.secure):
            raise ValidationError
        return instance

    def to_url(self, instance):
        if instance.private:
            return instance.secret
        return instance.name

class SecureCategoryConverter(CategoryConverter):
    secure = True
    regex = '[^/]{40}'

class ImageConverter(BaseConverter):
    secure = False
    regex = '[^/]{1,39}'

    def to_python(self, value):
        print "To Python IMG", value
        if self.secure:
            instance = Image.query.filter(Image.secret==value).first()
        else:
            instance = Image.query.get(int(value))
        if not instance or (instance and instance.private and not self.secure):
            raise ValidationError
        return instance

    def to_url(self, instance):
        print "To URL IMG", instance
        if instance.private:
            return instance.secret
        return str(instance.id)

class SecureImageConverter(CategoryConverter):
    secure = True
    regex = '[^/]{40}'


url_map = Map([
    Rule('/', endpoint='upload'),
    Rule('/upload/', endpoint='upload', defaults={'category': None}),
    Rule('/upload/<scat:category>', endpoint='upload'),
    Rule('/upload/<ncat:category>', endpoint='upload'),
    Rule('/categories', endpoint='categories'),
    Rule('/category/<scat:category>', endpoint='category'),
    Rule('/category/<ncat:category>', endpoint='category'),
    Rule('/thumb/<simg:image>', endpoint='thumbs'),
    Rule('/thumb/<nimg:image>', endpoint='thumbs'),
    Rule('/image/<simg:image>', endpoint='images'),
    Rule('/image/<nimg:image>', endpoint='images'),
    Rule('/show/<simg:image>', endpoint='show'),
    Rule('/show/<nimg:image>', endpoint='show'),
    Rule('/shared/<file>', endpoint='shared', build_only=True)
    ], converters={
        'ncat': CategoryConverter,
        'scat': SecureCategoryConverter,
        'nimg': ImageConverter,
        'simg': SecureImageConverter
    }
)

handlers = {
    'show':         views.show_image,
    'index':        views.index,
    'images':       views.serve_image,
    'thumbs':       views.serve_image,
#    'thumbs':       views.serve_thumbs,
    'upload':       views.upload,
    'invalid':      views.invalid,
    'category':     views.category_list,
    'categories':   views.categories_list,
}

