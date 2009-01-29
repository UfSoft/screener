# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from screener.utils import Response, generate_template

def invalid(request, **kw):
    return Response(generate_template('index.html', **{}))

def index(request, **kw):
    return Response(generate_template('index.html', **{}))


