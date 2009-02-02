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
    Rule('/', endpoint='index'),
    Rule('/upload', endpoint='upload'),
    Rule('/temp/<file>', endpoint='temp', build_only=True),
    Rule('/shared/<file>', endpoint='shared', build_only=True)
])

handlers = {
    'index':    views.index,
    'upload':   views.upload,
    'invalid':  views.invalid
}
