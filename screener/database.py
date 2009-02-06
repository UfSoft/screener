# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
from random import choice
from hashlib import sha1, md5
from os.path import basename, splitext
from sqlalchemy import and_
from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Boolean,
                        Binary)

from sqlalchemy import and_, or_
from sqlalchemy.orm import (create_session, scoped_session, relation, Query,
                            dynamic_loader, backref, deferred)

from sqlalchemy.ext.declarative import declarative_base

from screener.utils import application, local_manager, url_for

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

def new_db_session():
    """
    This function creates a new session if there is no session yet for
    the current context.  It looks up the application and if it finds
    one it creates a session bound to the active database engine in that
    application.  If there is no application bound to the context it
    raises an exception.
    """
    return create_session(application.database_engine, autoflush=True,
                          autocommit=False)

# and create a new global session factory.  Calling this object gives
# you the current active session
session = scoped_session(lambda: new_db_session(), local_manager.get_ident)


class ImageData(DeclarativeBase):
    __tablename__ = 'images_data'

    # Table Columns
    image_id  = Column(None, ForeignKey('images.id'), primary_key=True)
    original  = deferred(Column(Binary, nullable=False))
    resized   = deferred(Column(Binary, nullable=False))
    thumbnail = deferred(Column(Binary, nullable=False))

    # Query Object
    query = session.query_property(Query)

    def __init__(self, original, resized, thumbnail):
        self.original = original.read()
        self.resized = resized.read()
        self.thumbnail = thumbnail.read()


class Image(DeclarativeBase):
    __tablename__ = 'images'

    # Table Columns
    id            = Column(Integer, primary_key=True)
    filename     = Column("filename", String, nullable=False)
    extension     = Column(String(4), nullable=False)
    mime_type     = Column(String(15))
    stamp         = Column(DateTime, default=datetime.utcnow())
    description   = Column(String, default=u'')
    secret        = Column(String)
    private       = Column(Boolean, default=False)
    category_name = Column(None, ForeignKey('categories.name'))

    # ForeignKey Association
    _image        = relation(ImageData, backref="image", uselist=False,
                             cascade="all, delete, delete-orphan")
    category      = None # Associated elsewhere

    # Query Object
    query = session.query_property(Query)

    def __init__(self, filename, extension, mime_type, description=None,
                 private=False):
        self.filename = filename
        self.extension = extension
        self.mime_type = mime_type
        self.description = description
        self.private = private
        self.stamp = datetime.utcnow()
        if private:
            secret = sha1()
            secret.update(filename)
            secret.update(str(self.stamp))
            self.secret = secret.hexdigest()

    def add_image_data(self, original, resized, thumbnail):
        self._image = ImageData(original, resized, thumbnail)

    def __url__(self, image_type):
        print 'grabbing url of type', image_type
        if image_type == 'thumb':
            return url_for('thumb', image=self.private and self.secret or self.thumb_name)
        elif image_type == 'resized':
            return url_for('resized', image=self.private and self.secret or self.resized_name)
        elif image_type == 'image':
            return url_for('image', image=self.private and self.secret or self.image_name)
        elif image_type == 'show':
            return url_for('show', image=self.private and self.secret or self.image_name)

    @property
    def image_name(self):
        if self.private:
            return self.secret
        return "%s.%s" % (self.filename, self.extension)

    @property
    def thumb_name(self):
        if self.private:
            return self.secret
        return "%s.thumbnail.%s" % (self.filename, self.extension)

    @property
    def resized_name(self):
        if self.private:
            return self.secret
        return "%s.resized.%s" % (self.filename, self.extension)

    @property
    def etag(self):
        etag = md5(self.filename)
        etag.update(str(self.stamp))
        return etag.hexdigest()

    @property
    def format(self):
        return self.extension

    @property
    def image(self):
        return getattr(self._image, 'original')

    @property
    def resized(self):
#        print "grabbing resized",
        resized = getattr(self._image, 'resized')
#        print resized,
        if not resized:
#            print self.image
            return self.image
        return resized

    @property
    def thumb(self):
        return getattr(self._image, 'thumbnail')


class Category(DeclarativeBase):
    __tablename__ = 'categories'

    # Table Columns
    name        = Column(String, primary_key=True)
    stamp       = Column(DateTime, default=datetime.utcnow())
    description = Column(String)
    secret      = Column(String)
    private     = Column(Boolean, default=False)

    # ForeignKey Association
    images      = relation(Image, backref="category",
                                 cascade="all, delete, delete-orphan")

    # Query Object
    query = session.query_property(Query)

    def __init__(self, name, description=None, private=False):
        self.name = name
        self.description = description
        self.private = private
        self.stamp = datetime.utcnow()
        if private:
            secret = sha1()
            secret.update(name)
            secret.update(str(self.stamp))
            self.secret = secret.hexdigest()


    def __url__(self):
        if self.private:
            return url_for('category', category=self.secret)
        return url_for('category', category=self.name)

    @property
    def random(self):
        available_ids = session.query(Image.id).filter(
            and_(Image.private==False, Image.category==self)
        ).all()
        return Image.query.get(choice(available_ids))



