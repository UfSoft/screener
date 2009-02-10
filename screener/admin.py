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

def users(request):
    _users = User.query.all()
    if request.method == 'POST':
        if 'delete' in request.values:
            for user in _users:
                if user.uuid in request.values.getlist('uuid'):
                    session.delete(user)
            session.commit()
            _users = User.query.all()
    return generate_template('admin/users.html', users=_users)


def categories(request):
    _categories=Category.query.all()

    if request.method == 'POST':
        if 'delete' in request.values:
            print 'DELETE', request.values.getlist('name')
            for category in _categories:
                if category.name in request.values.getlist('name'):
                    session.delete(category)
            session.commit()
            _categories=Category.query.all()
        elif 'update' in request.values:
            print 'UPDATE', request.values.getlist('private')
            for category in _categories:
                category.private = category.name in \
                                            request.values.getlist('private')
    return generate_template('admin/categories.html',
                             categories=_categories)
