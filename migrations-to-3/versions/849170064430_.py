"""* add enqueue_job column to smtpserver table
* Add tokenowner table and move tokenuser data to new table
* Add column used_login to usercache
* Add column for triggered policies in Audit Table.
* shorten columns used in UNIQUE constraints in periodictasklastrun, periodictaskoption

Revision ID: 849170064430
Revises: 1a0710df148b
Create Date: 2018-08-03 12:36:17.091876

"""

revision = '849170064430'
down_revision = '1a0710df148b'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Sequence
from sqlalchemy import orm
from privacyidea.models import ResolverRealm, TokenRealm, Resolver
import sys

Base = declarative_base()

class Realm(Base):
    __tablename__ = 'realm'
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("realm_seq"), primary_key=True,
                   nullable=False)
    name = sa.Column(sa.Unicode(255), default=u'',
                     unique=True, nullable=False)
    default = sa.Column(sa.Boolean(), default=False)
    option = sa.Column(sa.Unicode(40), default=u'')


class TokenOwner(Base):
    __tablename__ = 'tokenowner'
    id = sa.Column(sa.Integer(), Sequence("tokenowner_seq"), primary_key=True)
    token_id = sa.Column(sa.Integer(), sa.ForeignKey('token.id'))
    token = orm.relationship('Token', lazy='joined', backref='token_list')
    resolver = sa.Column(sa.Unicode(120), default=u'', index=True)
    user_id = sa.Column(sa.Unicode(320), default=u'', index=True)
    realm_id = sa.Column(sa.Integer(), sa.ForeignKey('realm.id'))
    realm = orm.relationship('Realm', lazy='joined', backref='realm_list')


class Token(Base):
    __tablename__ = 'token'
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}
    id = sa.Column(sa.Integer, Sequence("token_seq"),
                   primary_key=True,
                   nullable=False)
    serial = sa.Column(sa.Unicode(40), default=u'',
                       unique=True,
                       nullable=False,
                       index=True)
    resolver = sa.Column(sa.Unicode(120), default=u'',
                        index=True)
    resolver_type = sa.Column(sa.Unicode(120), default=u'')
    user_id = sa.Column(sa.Unicode(320),
                       default=u'', index=True)


def upgrade():
    # First, try to create the table with the shorter field sizes.
    # This will fail if the tables already exist (which will be
    # the case in most installations)
    try:
        op.create_table('periodictasklastrun',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('node', sa.Unicode(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'node', name='ptlrix_1'),
        mysql_row_format='DYNAMIC'
        )
        op.create_table('periodictaskoption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periodictask_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.Unicode(length=255), nullable=False),
        sa.Column('value', sa.Unicode(length=2000), nullable=True),
        sa.ForeignKeyConstraint(['periodictask_id'], ['periodictask.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periodictask_id', 'key', name='ptoix_1'),
        mysql_row_format='DYNAMIC'
        )
        print('Successfully created shortened periodictasklastrun and periodictaskoption.')
    except Exception as exx:
        print('Creation of periodictasklastrun and periodictaskoption with shortened columns failed: {!r}'.format(exx))
        print('This is expected behavior if they were already present.')
    try:
        op.alter_column('periodictasklastrun', 'node',
                   existing_type=sa.VARCHAR(length=256),
                   type_=sa.Unicode(length=255),
                   existing_nullable=False)
        op.alter_column('periodictaskoption', 'key',
                   existing_type=sa.VARCHAR(length=256),
                   type_=sa.Unicode(length=255),
                   existing_nullable=False)
        print('Successfully shortened columns of periodictasklastrun and periodictaskoption.')
    except Exception as exx:
        print('Shortening of periodictasklastrun and periodictaskoption columns failed: {!r}'.format(exx))
        print('This is expected behavior if the columns have already been shorted.')

    try:
        op.add_column('pidea_audit', sa.Column('policies', sa.String(length=255), nullable=True))
    except Exception as exx:
        print('Adding of column "policies" in table pidea_audit failed: {!r}'.format(exx))
        print('This is expected behavior if this column already exists.')

    try:
        op.add_column('usercache', sa.Column('used_login', sa.Unicode(length=64), nullable=True))
        op.create_index(op.f('ix_usercache_used_login'), 'usercache', ['used_login'], unique=False)
    except Exception as exx:
        print('Adding of column "used_login" in table usercache failed: {!r}'.format(exx))
        print('This is expected behavior if this column already exists.')

    try:
        op.create_table('tokenowner',
        sa.Column('id', sa.Integer()),
        sa.Column('token_id', sa.Integer(), nullable=True),
        sa.Column('resolver', sa.Unicode(length=120), nullable=True),
        sa.Column('user_id', sa.Unicode(length=320), nullable=True),
        sa.Column('realm_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['realm_id'], ['realm.id'], ),
        sa.ForeignKeyConstraint(['token_id'], ['token.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_row_format='DYNAMIC'
        )
        op.create_index(op.f('ix_tokenowner_resolver'), 'tokenowner', ['resolver'], unique=False)
        op.create_index(op.f('ix_tokenowner_user_id'), 'tokenowner', ['user_id'], unique=False)
    except Exception as exx:
        print("Can not create table 'tokenowner'. It probably already exists")
        print (exx)

        # Now we drop the columns
        #op.drop_column('token', 'user_id')
        #op.drop_column('token', 'resolver')
        #op.drop_column('token', 'resolver_type')

    except Exception as exx:
        session.rollback()
        print("Failed to migrate token assignment data!")
        print (exx)

    try:
        op.add_column('smtpserver', sa.Column('enqueue_job', sa.Boolean(), nullable=False, server_default=sa.false()))
    except Exception as exx:
        print("Could not add column 'smtpserver.enqueue_job'")
        print(exx)
