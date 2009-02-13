# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.routing import Map, Rule, Submount
from screener import views, admin

url_map = Map([
    Rule('/', endpoint='index', redirect_to='upload'),
    Rule('/upload/', endpoint='upload', defaults={'category': None}),
    Rule('/upload/<category>', endpoint='upload'),
    Rule('/categories', endpoint='categories'),
    Submount('/abuse', [
        Rule('/confirm', endpoint='report', defaults={'hash': None}),
        Rule('/confirm/<hash>', endpoint='report'),
    ]),
    Submount('/category', [
        Rule('/<category>', endpoint='category'),
        Rule('/<category>/thumb/<image>', endpoint='thumb'),
        Rule('/<category>/resized/<image>', endpoint='resized'),
        Rule('/<category>/image/<image>', endpoint='image'),
        Rule('/<category>/show/<image>', endpoint='show'),
        Rule('/<category>/report/<image>', endpoint='abuse')
    ]),
    Rule('/shared/<file>', endpoint='shared', build_only=True),
    Submount('/manage', [
        Rule('/', endpoint='admin', redirect_to='/manage/users'),
        Rule('/users', endpoint='admin/users'),
        Rule('/categories', endpoint='admin/categories'),
        Rule('/authenticate', endpoint='admin/login'),
        Rule('/logout', endpoint='admin/logout'),
    ])
])

handlers = {
    # Regular Views
    'show':         views.show_image,
    'index':        views.index,
    'image':        views.serve_image,
    'thumb':        views.serve_image,
    'resized':      views.serve_image,
    'upload':       views.upload,
    'category':     views.category_list,
    'categories':   views.categories_list,
    'abuse':        views.report_abuse,
    'report':       views.report_abuse_confirm,

    # Administration Views
    'admin':            admin.users,
    'admin/login':      admin.login,
    'admin/logout':     admin.logout,
    'admin/users':      admin.users,
    'admin/categories': admin.categories
}

