# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from screener.database import session, User, Change
from screener.utils import generate_template, flash, url_for
from screener.utils.crypto import gen_pwhash
from werkzeug.exceptions import NotFound, Unauthorized
from werkzeug.utils import redirect

def login(request):
    if request.method== "POST":
        username = request.values.get('username')
        password = request.values.get('password')
        user = User.query.filter(User.username==username).first()
        if not user:
            return generate_template("account/login.html",
                                     formfill=request.values,
                                     error="User is not known.")
        if not user.authenticate(password):
            return generate_template("account/login.html",
                                     formfill=request.values,
                                     error="Authentication failed.")
        if not user.confirmed:
            return generate_template("account/login.html",
                                     formfill=request.values,
                                     error="This account hasn't been "
                                           "confirmed yet.")
        request.login(user, permanent=True)
    if request.user.is_admin:
        return redirect(url_for('admin'))
    return generate_template("account/login.html")


def logout(request):
    request.session.clear()
    return redirect(url_for('upload'))

def preferences(request):
    """Return the user configurable prefences"""
    if not request.user.confirmed:
        raise Unauthorized
    if request.method == 'POST':
        new_email = request.values.get('email')
        new_password = request.values.get('password')
        new_password_confirm = request.values.get('password_confirm')
        if new_password and not new_password_confirm:
            flash("You need to confirm your password")
            return generate_template('preferences.html',
                                     user=request.user,
                                     formfill=request.values)
        elif not new_password and new_password_confirm:
            flash("Can't confirm an empty password")
            return generate_template('preferences.html',
                                     user=request.user,
                                     formfill=request.values)
        elif new_password and new_password_confirm:
            if new_password != new_password_confirm:
                flash("Passwords do not match")
                return generate_template('preferences.html',
                                         user=request.user,
                                         formfill=request.values)
            request.user.password = new_password
        if new_email != request.user.email:
            change = Change('email', new_email)
            change.owner = request.user
            session.add(change)
            session.commit()
            request.notification.sendmail(
                "Account Change Confirmation", 'email_change.txt',
                {'change': change}, new_email
            )
            flash("An email message was sent to %s in order to confirm the "
                  "address. Until confirmed, your old address is still in "
                  "use." % new_email)
        return redirect(url_for('account.prefs'))

    return generate_template('account/preferences.html', user=request.user)

def reset(request):
    if request.method == 'POST':
        email = request.values.get('email')
        new_password = request.values.get('password')
        new_password_confirm = request.values.get('password_confirm')
        if not email:
            flash("In order to reset a password, you need to provide an email "
                  "address", True)
            return generate_template('account/reset.html')
        user = User.query.filter(User.email==email).first()
        if not user:
            flash("No user is known by this email address", True)
            return generate_template('account/reset.html')
        if new_password != new_password_confirm:
            flash("The passwords do not match", True)
            return generate_template('account/reset.html',
                                     formfill=request.values)
        change = Change('passwd_hash', gen_pwhash(new_password))
        change.owner = user
        session.add(change)
        session.commit()
        request.notification.sendmail(
                "Account Change Confirmation", 'password_reset.txt',
                {'change': change}, email
            )
        flash("An email message was sent to %s in order to confirm the "
              "password change. Until confirmed, your old password is still in "
              "use." % email)
    return generate_template('account/reset.html')

def register(request):
    if request.method == 'POST':
        email = request.values.get('email')
        username = request.values.get('username')
        password = request.values.get('password')
        password_confirm = request.values.get('password_confirm')
        for value in (email, username, password, password_confirm):
            if not value:
                flash("All fields are required", True)
                return generate_template('account/register.html',
                                         formfill=request.values)
        if User.query.filter(User.username==username).first():
            flash("The username you asked for is already taken", True)
            return generate_template('account/register.html',
                                     formfill=request.values)
        if User.query.filter(User.email==email).first():
            flash("A user with this email address already exists", True)
            return generate_template('account/register.html',
                                     formfill=request.values)
        if password != password_confirm:
            flash("Passwords do not match", True)
            return generate_template('account/register.html',
                                     formfill=request.values)
        user = User(username, email, passwd=password)
        session.add(user)
        change = Change('confirmed', False)
        change.owner = user
        session.add(change)
        session.commit()
        request.notification.sendmail(
            "New Account Confirmation", 'register.txt',
            {'change': change}, email
        )
        flash("An email message was sent to %s in order to confirm the "
              "new account. Until confirmed, you won't be able to login."
              % email)

    return generate_template('account/register.html')

def confirm(request, hash=None):
    hash = request.values.get('confirm_hash', hash)
    if not hash:
        flash("Please insert the hash you were given")
        return generate_template('account/confirm.html')
    else:
        change = Change.query.get(hash)
        setattr(change.owner, change.name, change.value)
        session.delete(change)
        session.commit()
        flash("The requested change was confirmed")
        return redirect(url_for('index'))
