# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
import string
from random import choice
from hashlib import sha1, md5

SALT_CHARS = string.ascii_lowercase + string.digits
SECRET_KEY_CHARS = string.ascii_letters + string.digits + string.punctuation

def gen_salt(length=6):
    """Generate a random string of SALT_CHARS with specified ``length``."""
    if length <= 0:
        raise ValueError('requested salt of length <= 0')
    return ''.join(choice(SALT_CHARS) for _ in xrange(length))

def gen_secret_key():
    """Generate a new secret key."""
    return ''.join(choice(SECRET_KEY_CHARS) for _ in xrange(64))

def gen_pwhash(password):
    """Return a the password encrypted in sha format with a random salt."""
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    salt = gen_salt(6)
    h = sha1()
    h.update(salt)
    h.update(password)
    return 'sha$%s$%s' % (salt, h.hexdigest())

def check_pwhash(pwhash, password):
    """Check a password against a given hash value. Since many forums save md5
    passwords with no salt and it's technically impossible to convert this to
    an sha hash with a salt we use this to be able to check for plain
    passwords::

        plain$$default

    md5 passwords without salt::

        md5$$c21f969b5f03d33d43e04f8f136e7682

    md5 passwords with salt::

        md5$123456$7faa731e3365037d264ae6c2e3c7697e

    sha passwords::

        sha$123456$118083bd04c79ab51944a9ef863efcd9c048dd9a
    """
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    if pwhash.count('$') < 2:
        return False
    method, salt, hashval = pwhash.split('$', 2)
    if method == 'plain':
        return hashval == password
    elif method == 'md5':
        h = md5()
    elif method == 'sha':
        h = sha1()
    else:
        return False
    h.update(salt)
    h.update(password)
    return h.hexdigest() == hashval
