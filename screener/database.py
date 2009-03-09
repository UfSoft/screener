# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
from datetime import datetime
from hashlib import sha1, md5
from os import remove, removedirs
from os.path import basename, splitext, dirname, join, islink, getsize
from random import choice
from screener.utils import application, local, local_manager, url_for
from screener.utils.crypto import gen_pwhash, check_pwhash
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Boolean,
                        PickleType, and_, or_)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (create_session, scoped_session, relation, Query,
                            deferred, dynamic_loader, backref, MapperExtension,
                            EXT_CONTINUE)
from uuid import uuid4


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

class DeleteMapperExtension(MapperExtension):
    def after_delete(self, mapper, connection, instance):
        if hasattr(instance, '__delete__'):
            instance.__delete__()
        return EXT_CONTINUE

# and create a new global session factory.  Calling this object gives
# you the current active session
session = scoped_session(lambda: new_db_session(), local_manager.get_ident)


class User(DeclarativeBase):
    __tablename__ = 'users'

    uuid                = Column(String(32), primary_key=True)
    username            = Column(String, index=True)
    email               = Column(String)
    confirmed           = Column(Boolean, default=False)
    passwd_hash         = Column(String)
    last_visit          = Column(DateTime, default=datetime.utcnow())
    last_login          = Column(DateTime, default=datetime.utcnow())
    disk_usage          = deferred(Column(PickleType,
                                         default=dict(images=0, resized=0,
                                                      thumbs=0, abuse=0)))
    show_adult_content  = Column(Boolean, default=False)
    agreed_to_tos       = Column(Boolean, default=False)
    is_admin            = Column(Boolean, default=False)

    images              = dynamic_loader("Image", backref='owner',
                                         cascade="all, delete, delete-orphan")
    reports             = dynamic_loader("Abuse", backref='owner',
                                         cascade="all, delete, delete-orphan")
    categories          = dynamic_loader("Category", backref='owner',
                                         cascade="all, delete, delete-orphan")
    changes             = relation("Change", backref='owner',
                                   cascade="all, delete, delete-orphan")
    leecher             = relation("Leecher", backref='owner',
                                   cascade="all, delete, delete-orphan")

    # Query Object
    query = session.query_property(Query)

    def __init__(self, username=None, email=None, confirmed=False, passwd=None,
                 is_admin=False, show_adult_content=False, agreed_to_tos=False):
        self.uuid = uuid4().hex
        self.username = username
        if email:
            self.email = email
        if passwd:
            self.passwd_hash = gen_pwhash(passwd)
        self.confirmed = confirmed
        self.show_adult_content = show_adult_content
        self.agreed_to_tos = agreed_to_tos
        self.is_admin = is_admin

    def dict(self):
        return {
            'uuid': self.uuid,
            'username': self.username,
            'email': self.email,
            'confirmed': self.confirmed,
            'last_visit': self.last_visit,
            'last_login': self.last_login
        }

    def __repr__(self):
        return "<User (%s) UUID:%s>" % (self.username or 'annonymous', self.uuid)

    def authenticate(self, password):
        if self.confirmed and check_pwhash(self.passwd_hash, password):
            self.update_last_visit()
            self.last_login = datetime.utcnow()
            session.commit()
            return True
        return False

    def update_last_visit(self):
        self.last_visit = datetime.utcnow()

    def update_disk_usage(self):
        images = resized = thumbs = abuse = 0
        for image in self.images:
            if image.abuse:
                abuse += getsize(image.image_path) + getsize(image.thumb_path)
                if not islink(image.resized_path):
                    abuse += getsize(image.resized_path)
            else:
                images += getsize(image.image_path)
                thumbs += getsize(image.thumb_path)
                if not islink(image.resized_path):
                    resized += getsize(image.resized_path)

        self.disk_usage = dict(
            images=images,
            resized=resized,
            thumbs=thumbs,
            abuse=abuse
        )


class Change(DeclarativeBase):
    __tablename__ = 'persistent'

    hash = Column('id', String(32), primary_key=True)
    name = Column(String)
    value = Column(String)
    owner_uid = Column(None, ForeignKey('users.uuid'))

    # ForeignKey Association
    owner     = None   # Defined on User.changes

    # Query Object
    query = session.query_property(Query)


    def __init__(self, name=None, value=None):
        self.hash = uuid4().hex
        self.name = name
        self.value = value

    def __url__(self, include_hash=True, **kwargs):
        return url_for('account.confirm',
                       hash=include_hash and self.hash or None, **kwargs)


class Leecher(DeclarativeBase):
    __tablename__ = 'leechers'

    key       = Column(String(32), primary_key=True)
    owner_uid = Column(None, ForeignKey('users.uuid'))

    # ForeignKey Association
    owner     = None   # Defined on User.categories

    domains   = relation("LeechDomain", backref='domains',
                         cascade="all, delete, delete-orphan")

    # Query Object
    query = session.query_property(Query)

    def __init__(self, owner):
        key = md5(application.config.secret_key)
        key.update(owner.uuid)
        self.key = key.hexdigest()


class LeechDomain(DeclarativeBase):
    __tablename__ = 'leecher_domains'

    id        = Column(Integer, primary_key=True, autoincrement=True)
    domain    = Column(String, nullable=False)
    leech_key = Column(None, ForeignKey('leechers.key'))

    # Query Object
    query = session.query_property(Query)


class Abuse(DeclarativeBase):
    __tablename__ = 'reports'

    # Table Columns
    hash           = Column(String(40), primary_key=True)
    issued         = deferred(Column(DateTime))
    confirmed      = Column(Boolean, default=False)
    reason         = deferred(Column(String))
    reporter_ip    = deferred(Column(String(15)))
    reporter_email = deferred(Column(String))
    owner_uid      = Column(None, ForeignKey('users.uuid'))
    image_id       = Column(None, ForeignKey('images.id'))

    owner          = None   # Defined on User.reports

    # Query Object
    query = session.query_property(Query)

    def __init__(self, image, reason, reporter_ip, reporter_email):
        self.image = image
        self.reason = reason
        self.reporter_ip = reporter_ip
        self.reporter_email = reporter_email
        self.owner = local.request.user
        self.issued = datetime.utcnow()
        confirm_hash = sha1(self.owner.uuid)
        confirm_hash.update(image.id)
        confirm_hash.update(reason)
        confirm_hash.update(reporter_ip)
        confirm_hash.update(reporter_email)
        confirm_hash.update(str(self.issued))
        self.hash = confirm_hash.hexdigest()

    def __url__(self, include_hash=True, **kwargs):
        return url_for('report', hash=include_hash and self.hash or None,
                       **kwargs)


class Image(DeclarativeBase):
    __tablename__ = 'images'
    __mapper_args__ = {'extension': DeleteMapperExtension()}

    # Table Columns
    id             = Column(String(40), primary_key=True)
    filename       = Column("filename", String, nullable=False, index=True)
    path           = Column("path", String, nullable=False)
    mimetype       = Column(String(15))
    stamp          = Column(DateTime, default=datetime.utcnow())
    description    = Column(String, default=u'')
    submitter_ip   = Column(String(15))
    private        = Column(Boolean, default=False)
    adult_content  = Column(Boolean, default=False)
    views          = Column(Integer, default=0)
    category_name  = Column(None, ForeignKey('categories.name'))
    owner_uid      = Column(None, ForeignKey('users.uuid'))

    # ForeignKey Association
    abuse         = relation(Abuse, backref='image', uselist=False,
                             cascade="all, delete, delete-orphan")
    owner         = None   # Defined on User.images
    category      = None # Associated elsewhere

    # Query Object
    query = session.query_property(Query)

    def __init__(self, filepath, mimetype, description=None,
                 private=False, submitter_ip=None, adult_content=False):
        self.stamp = datetime.utcnow()
        image_id = sha1(filepath)
        image_id.update(str(self.stamp))
        self.id = image_id.hexdigest()
        self.filename = basename(filepath)
        self.path = dirname(filepath)
        self.mimetype = mimetype
        self.description = description
        self.private = private
        self.adult_content = adult_content
        self.submitter_ip = submitter_ip
        self.owner = local.request.user

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
        elif image_type == 'abuse':
            return url_for(
                'abuse', image=self.private and self.id or self.image_name,
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


    def __delete__(self):
        for path in [self.image_path, self.thumb_path, self.resized_path]:
            try:
                remove(path)
            except OSError:
                # File does not exist!?
                pass
        try:
            removedirs(self.path)
        except OSError:
            # Directory not empty
            pass


class Category(DeclarativeBase):
    __tablename__ = 'categories'

    # Table Columns
    name        = Column(String(40), primary_key=True)
    secret      = Column(String(40), index=True)
    stamp       = Column(DateTime, default=datetime.utcnow())
    description = Column(String)
    private     = Column(Boolean, default=False)
    owner_uid   = Column(None, ForeignKey('users.uuid'))

    # ForeignKey Association
    images      = dynamic_loader(Image, backref="category",
                                 cascade="all, delete, delete-orphan")
    owner       = None   # Defined on User.categories

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
        self.owner = local.request.user

    def __url__(self):
        if self.private:
            return url_for('category', category=self.secret)
        return url_for('category', category=self.name)

    @classmethod
    def visible(self):
        if local.request.user.is_admin:
            # User is an Admin, return all categories, his and not his
            return Category.query.all()

        return Category.query.filter(
            or_(Category.private==False,
                and_(Category.private==True,
                     Category.owner==local.request.user
                )
            )
        ).all()

    @property
    def random(self):
        user = local.request.user
        if user.is_admin:
            available_ids = session.query(Image.id).filter(
                Image.category==self
            ).all()
        else:
            user = local.request.user
            available_ids = session.query(Image.id).filter(
                or_(and_(Image.category==self,
                         Image.private==False, Image.abuse==None,
                         Image.adult_content.in_([False,
                                                  user.show_adult_content])),
                    and_(Image.private==True, Image.abuse==None,
                         Image.category==self, Image.owner==user
                    )
                )
            ).all()
        if available_ids:
            return Image.query.get(choice([id[0] for id in available_ids]))
        return []

    def visible_images(self):
        user = local.request.user
        if user.is_admin:
            # User is an Admin, return all images
            return self.images
        return Image.query.filter(
            or_(and_(Image.category==self,
                     Image.private==False, Image.abuse==None,
                     Image.adult_content.in_([False, user.show_adult_content])),
                and_(Image.private==True, Image.abuse==None,
                     Image.category==self, Image.owner==user
                )
            )
        ).all()

