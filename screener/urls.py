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
])

handlers = {
    'index':    views.index,
    'invalid':  views.invalid
}
