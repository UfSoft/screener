# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
from werkzeug.exceptions import Unauthorized
from werkzeug.utils import redirect

from screener.database import session, User, Category
from screener.utils import url_for, generate_template, Response

def users(request):
    if not request.user.is_admin:
        raise Unauthorized
    for user in User.query.all():
        print user, user.categories.count()
    return generate_template('admin/users.html', users=User.query.all())

def login(request):
    if request.method== "POST":
        username = request.values.get('username')
        password = request.values.get('password')
        user = User.query.filter(User.username==username).first()
        if not user:
            return generate_template("admin/auth.html", formfill=request.values,
                                     error="User is not known.")
        if not user.authenticate(password):
            return generate_template("admin/auth.html", formfill=request.values,
                                     error="Authentication failed.")
        request.login(user, permanent=True)
    if request.user.is_admin:
        return redirect(url_for('admin'))
    return generate_template("admin/auth.html")


def logout(request):
    request.session.clear()
    return redirect(url_for('upload'))

