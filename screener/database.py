# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
from random import choice
from hashlib import sha1, md5
from os.path import basename, splitext, dirname, join
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean

from sqlalchemy import and_, or_
from sqlalchemy.orm import create_session, scoped_session, relation, Query

from sqlalchemy.ext.declarative import declarative_base

from screener.utils import application, local, local_manager, url_for

ABUSE_UNREPORTED, ABUSE_REPORTED, ABUSE_CONFIRMED = range(3)

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


class Image(DeclarativeBase):
    __tablename__ = 'images'

    # Table Columns
    id             = Column(String(40), primary_key=True)
    filename       = Column("filename", String, nullable=False, index=True)
    path           = Column("path", String, nullable=False)
    mimetype       = Column(String(15))
    stamp          = Column(DateTime, default=datetime.utcnow())
    description    = Column(String, default=u'')
    submitter_ip   = Column(String(15))
    private        = Column(Boolean, default=False)
    abuse_status   = Column(Integer, default=0)
    category_name  = Column(None, ForeignKey('categories.name'))

    category      = None # Associated elsewhere

    # Query Object
    query = session.query_property(Query)

    def __init__(self, filepath, mimetype, description=None,
                 private=False, submitter_ip=None):
        self.stamp = datetime.utcnow()
        image_id = sha1(filepath)
        image_id.update(str(self.stamp))
        self.id = image_id.hexdigest()
        self.filename = basename(filepath)
        self.path = dirname(filepath)
        self.mimetype = mimetype
        self.description = description
        self.private = private
        submitter_ip = submitter_ip

    def __url__(self, image_type):
        category = self.category.private and self.category.secret or \
                                                            self.category.name
        if image_type == 'thumb':
            return url_for(
                'thumb', image=self.private and self.id or self.thumb_name,
                category=category)
        elif image_type == 'resized':
            return url_for(
                'resized',  image=self.private and self.id or self.resized_name,
                category=category)
        elif image_type == 'image':
            return url_for(
                'image', image=self.private and self.id or self.image_name,
                category=category)
        elif image_type == 'show':
            return url_for(
                'show', image=self.private and self.id or self.image_name,
                category=category)

    @property
    def _filename_no_extension(self):
        if not hasattr(self, '__filename'):
            self.__filename, self.extension = splitext(self.filename)
        return self.__filename

    @property
    def image_name(self):
        return self.private and self.id or self.filename

    @property
    def thumb_name(self):
        if self.private:
            return self.id
        return "%s.thumbnail%s" % (self._filename_no_extension, self.extension)

    @property
    def resized_name(self):
        if self.private:
            return self.id
        return "%s.resized%s" % (self._filename_no_extension, self.extension)

    @property
    def image_path(self):
        return join(self.path, self.filename)

    @property
    def thumb_path(self):
        return join(self.path, "%s.thumbnail%s" % (self._filename_no_extension,
                                                   self.extension))

    @property
    def resized_path(self):
        return join(self.path, "%s.resized%s" % (self._filename_no_extension,
                                                 self.extension))

    @property
    def etag(self):
        etag = md5(self.id)
        etag.update(str(self.stamp))
        return etag.hexdigest()


class Category(DeclarativeBase):
    __tablename__ = 'categories'

    # Table Columns
    name        = Column(String(40), primary_key=True)
    secret      = Column(String(40), index=True)
    stamp       = Column(DateTime, default=datetime.utcnow())
    description = Column(String)
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
        secret = sha1(name)
        secret.update(str(self.stamp))
        self.secret = secret.hexdigest()

    def __url__(self):
        if self.private:
            return url_for('category', category=self.secret)
        return url_for('category', category=self.name)

    @property
    def random(self):
        available_ids = session.query(Image.id).filter(
            or_(and_(Image.private==False, Image.abuse_status==0,
                     Image.category==self),
                and_(Image.private==True, Image.abuse_status==0,
                     Image.category==self,
                     Image.id.in_(local.request.session.get('secrets', [])))
            )
        ).all()
        return Image.query.get(choice(available_ids))

    def visible_images(self):
        return Image.query.filter(
            or_(and_(Image.private==False, Image.abuse_status==0,
                     Image.category==self),
                and_(Image.private==True, Image.abuse_status==0,
                     Image.category==self,
                     Image.id.in_(local.request.session.get('secrets', [])))
            )
        ).all()
