# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.routing import Map, Rule, Subdomain, Submount
from screener import views, services

url_map = Map([
    Rule('/', endpoint='index', redirect_to='upload'),
    Rule('/tos', endpoint='tos'),
    Submount('/account', [
        Rule('/login', endpoint="account.login"),
        Rule('/logout', endpoint="account.logout"),
        Rule('/reset', endpoint="account.reset"),
        Rule('/delete', endpoint="account.delete"),
        Rule('/register', endpoint="account.register"),
        Rule('/preferences', endpoint="account.prefs"),
        Rule('/preferences/anonymous', endpoint="account.anonpref"),
        Rule('/verify', endpoint="account.verify"),
        Rule('/confirm/', endpoint="account.confirm", defaults={'hash': None}),
        Rule('/confirm/<hash>', endpoint="account.confirm"),
    ]),
    Rule('/upload', endpoint='upload', defaults={'category': None}),
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
        Rule('/<category>/report/<image>', endpoint='abuse'),
        Subdomain('<leecher>', [
#            Rule('/<category>', endpoint='category'),
            Rule('/<category>/thumb/<image>', endpoint='thumb'),
            Rule('/<category>/resized/<image>', endpoint='resized'),
#            Rule('/<category>/image/<image>', endpoint='image'),
            Rule('/<category>/show/<image>', endpoint='show'),
            Rule('/<category>/report/<image>', endpoint='abuse')
        ]),
    ]),
    Rule('/shared/<file>', endpoint='shared', subdomain='', build_only=True),
    Submount('/manage', [
        Rule('/', endpoint='admin', redirect_to='/manage/users'),
        Rule('/users', endpoint='admin/users'),
        Rule('/categories', endpoint='admin/categories'),
    ]),
    #Rule('/_services', endpoint="services")
], default_subdomain='', strict_slashes=True)

handlers = {
    # Regular Views
    'tos':              views.base.tos,
    'show':             views.base.show_image,
    'image':            views.base.serve_image,
    'thumb':            views.base.serve_image,
    'resized':          views.base.serve_image,
    'upload':           views.base.upload,
    'category':         views.base.category_list,
    'categories':       views.base.categories_list,
    'abuse':            views.base.report_abuse,
    'report':           views.base.report_abuse_confirm,

    # Authentication/Prefs Views
    'account.login':    views.account.login,
    'account.logout':   views.account.logout,
    'account.prefs':    views.account.preferences,
    'account.anonpref': views.account.anonymous_preferences,
    'account.reset':    views.account.reset,
    'account.confirm':  views.account.confirm,
    'account.register': views.account.register,

    # Administration Views
    'admin':            views.admin.users,
    'admin/users':      views.admin.users,
    'admin/categories': views.admin.categories,

    # RPC Services
    #'services':         services.service
}

