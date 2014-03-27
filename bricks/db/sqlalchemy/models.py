# -*- encoding: utf-8 -*-
"""
SQLAlchemy models for baremetal data.
"""

import json
import urlparse

from oslo.config import cfg

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Integer, Index
from sqlalchemy import schema, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR

from bricks.openstack.common.db.sqlalchemy import models

sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]

cfg.CONF.register_opts(sql_opts, 'database')


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database_connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JsonEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = json.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JSONEncodedDict(JsonEncodedType):
    """Represents dict serialized as json-encoded string in db."""
    type = dict


class JSONEncodedList(JsonEncodedType):
    """Represents list serialized as json-encoded string in db."""
    type = list


class BricksBase(models.TimestampMixin,
                 models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative_base(cls=BricksBase)


class BrickConfig(Base):
    """An entire brick configuration."""

    __tablename__ = 'brickconfig'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_brickconfig0uuid'),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    version = Column(String(255))
    is_public = Column(Boolean, default=False)
    tenant_id = Column(String(255))

    tag = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo = Column(String(255), nullable=True)
    app_version = Column(String(36), nullable=True)
    minimum_requirement = Column(String(36), nullable=True)

    ports = Column(JSONEncodedList, nullable=True)
    # environ is going to exist as a DICT for now and use weights for ordering.
    environ = Column(JSONEncodedDict, nullable=True)
    email_template = Column(Text, nullable=True)


class BrickConfigFile(Base):
    __tablename__ = 'brickconfig_file'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_brickconfig_file0uuid'),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    description = Column(Text, nullable=True)
    contents = Column(Text, nullable=True)



class Brick(Base):
    """A Brick."""

    __tablename__ = 'brick'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_brick0uuid'),
        Index('brick_config_uuid', 'brickconfig_uuid'),
        Index('brick_tenant_id', 'tenant_id'),
        Index('brick_instance_uuid', 'instance_id')
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    brickconfig_uuid = Column(String(36), nullable=True)

    deployed_at = Column(DateTime, nullable=True)
    instance_id = Column(String(36))
    tenant_id = Column(String(255))
    status = Column(String(36))
    configuration = Column(JSONEncodedDict)
    deploy_log = Column(Text)
