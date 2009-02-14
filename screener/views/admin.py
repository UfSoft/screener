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
    if not request.user.is_admin:
        raise Unauthorized
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
