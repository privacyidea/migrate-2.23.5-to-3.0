#!/usr/bin/env python
from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Sequence
from sqlalchemy import orm
from sqlalchemy.orm import sessionmaker
from privacyidea.models import ResolverRealm, TokenRealm, Resolver
from privacyidea.app import create_app
import sys

# Read the SQL URI from the existing pi.cfg
app = create_app(config_name="production",
                 config_file="/etc/privacyidea/pi.cfg", silent=True)
PRIVACYIDEA_URI = app.config.get("SQLALCHEMY_DATABASE_URI")

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


privacyidea_engine = create_engine(PRIVACYIDEA_URI)
session = sessionmaker(bind=privacyidea_engine)()
conn_pi = privacyidea_engine.connect()

i = 0
# For each token, that has an owner, create a tokenowner entry
for token in session.query(Token).filter(Token.user_id != "", Token.user_id.isnot(None)):
    is_token_assigned = session.query(TokenOwner).filter(TokenOwner.token_id == token.id).all()
    i += 1
    if is_token_assigned:
        print("{0!s}: Token {1!s} already assigned to A user.".format(i, token.serial))
    else:
        token_realms = session.query(TokenRealm).filter(TokenRealm.token_id == token.id).all()
        print("{0!s}: Assigning token {1!s}.".format(i, token.serial))
        realm_id = None
        if not token_realms:
            sys.stderr.write(u"{serial!s}, {userid!s}, {resolver!s}, "
                             u"Error while migrating token assignment. "
                             u"This token has no realm assignments!\n".format(serial=token.serial,
                                                                              userid=token.user_id,
                                                                              resolver=token.resolver))
        elif len(token_realms) == 1:
            realm_id = token_realms[0].realm_id
        elif len(token_realms) > 1:
            # The token has more than one realm.
            # In order to figure out the right realm, we first fetch the token's resolver
            resolver = session.query(Resolver).filter_by(name=token.resolver).first()
            if not resolver:
                sys.stderr.write(u"{serial!s}, {userid!s}, {resolver!s}, "
                                 u"The token is assigned, but the assigned resolver can not "
                                 u"be found!\n".format(serial=token.serial,
                                                       userid=token.user_id,
                                                       resolver=token.resolver))
            else:
                # Then, fetch the list of ``Realm`` objects in which the token resolver is contained.
                resolver_realms = [r.realm for r in resolver.realm_list]
                if not resolver_realms:
                    sys.stderr.write(u"{serial!s}, {userid!s}, {resolver!s}, "
                                     u"The token is assigned, but the assigned resolver is not "
                                     u"contained in any realm!\n".format(serial=token.serial,
                                                                         userid=token.user_id,
                                                                         resolver=token.resolver))
                elif len(resolver_realms) == 1:
                    # The resolver is only in one realm, so this is the new realm of the token!
                    realm_id = resolver_realms[0].id
                elif len(resolver_realms) > 1:
                    # The resolver is contained in more than one realm, we have to apply more logic
                    # between the realms in which the resolver is contained and the realms,
                    # to which the token is assigend.
                    # More specifically, we find all realms which are both a token realm and
                    # a realm of the token resolver.
                    # If there is exactly one such realm, we have found our token owner realm.
                    # If there is more than one such realm, we cannot uniquely identify a token owner realm.
                    # If there is no such realm, we have an inconsistent database.
                    found_realm_ids = []
                    found_realm_names = []
                    for token_realm in token_realms:
                        if token_realm.realm in resolver_realms:
                            # The token realm, that also fits the resolver_realm is used as owner realm
                            found_realm_ids.append(token_realm.realm.id)
                            found_realm_names.append(token_realm.realm.name)
                    if len(found_realm_ids) > 1:
                        sys.stderr.write(u"{serial!s}, {userid!s}, {resolver!s}, Can not assign token. "
                                         u"Your realm configuration for the token is not distinct! "
                                         u"The tokenowner could be in multiple realms! "
                                         u"The token is assigned to the following realms and the resolver is also "
                                         u"contained in these realm IDs: {realms!s}.\n".format(serial=token.serial,
                                                                                               userid=token.user_id,
                                                                                               resolver=token.resolver,
                                                                                               realms=found_realm_names))
                    elif len(found_realm_ids) == 1:
                        realm_id = found_realm_ids[0]
                    else:
                        sys.stderr.write(u"{serial!s}, {userid!s}, {resolver!s}, "
                                         u"Can not assign token. The resolver is not contained in any "
                                         u"realms, to which the token is assigned!\n".format(serial=token.serial,
                                                                                             userid=token.user_id,
                                                                                             resolver=token.resolver))
        # If we could not figure out a tokenowner realm, we skip the token assignment.
        if realm_id is not None:
            to = TokenOwner(token_id=token.id, user_id=token.user_id,
                            resolver=token.resolver, realm_id=realm_id)
            session.add(to)
session.commit()
