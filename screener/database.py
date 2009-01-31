# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from datetime import datetime
from sqlalchemy import (Table, Column, Integer, String, DateTime, ForeignKey,
                        MetaData, join)

from sqlalchemy.orm import relation, create_session, scoped_session, mapper
from screener.utils import application, local_manager

metadata = MetaData()

def new_db_session():
    """
    This function creates a new session if there is no session yet for
    the current context.  It looks up the application and if it finds
    one it creates a session bound to the active database engine in that
    application.  If there is no application bound to the context it
    raises an exception.
    """
    return create_session(application.database_engine, autoflush=True,
                          transactional=True)

# and create a new global session factory.  Calling this object gives
# you the current active session
session = scoped_session(new_db_session, local_manager.get_ident)

category_table = Table('categories', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False),
    Column('stamp', DateTime, default=datetime.utcnow()),
    Column('secret', String),
)

image_table = Table('images', metadata,
    Column('id', Integer, primary_key=True),
    Column('filename', String, nullable=False),
    Column('stamp', DateTime, default=datetime.utcnow()),
    Column('description', String),
    Column('secret', String),
)
