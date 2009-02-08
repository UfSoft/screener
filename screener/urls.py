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
    Rule('/category/<category>/thumb/<image>', endpoint='thumb'),
    Rule('/category/<category>/resized/<image>', endpoint='resized'),
    Rule('/category/<category>/image/<image>', endpoint='image'),
    Rule('/category/<category>/show/<image>', endpoint='show'),
    Rule('/category/<category>/report/<image>', endpoint='abuse'),
    Rule('/shared/<file>', endpoint='shared', build_only=True)
])

handlers = {
    'show':         views.show_image,
    'index':        views.index,
    'image':        views.serve_image,
    'thumb':        views.serve_image,
    'resized':      views.serve_image,
    'upload':       views.upload,
    'category':     views.category_list,
    'categories':   views.categories_list,
    'abuse':        views.report_abuse
}

