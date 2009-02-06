# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.routing import Map, Rule
from screener import views

url_map = Map([
    Rule('/', redirect_to='upload'),
    Rule('/upload/', endpoint='upload', defaults={'category': None}),
    Rule('/upload/<category>', endpoint='upload'),
    Rule('/categories', endpoint='categories'),
    Rule('/category/<category>', endpoint='category'),
    Rule('/thumb/<image>', endpoint='thumb'),
    Rule('/resized/<image>', endpoint='resized'),
    Rule('/image/<image>', endpoint='image'),
    Rule('/show/<image>', endpoint='show'),
    Rule('/shared/<file>', endpoint='shared', build_only=True)
])

handlers = {
    'show':         views.show_image,
    'index':        views.index,
    'image':        views.serve_image,
    'thumb':        views.serve_image,
    'resized':      views.serve_image,
    'upload':       views.upload,
    'invalid':      views.invalid,
    'category':     views.category_list,
    'categories':   views.categories_list,
}

