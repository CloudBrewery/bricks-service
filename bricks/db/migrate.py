"""Database setup and migration commands."""

from oslo.config import cfg

from bricks.common import utils

CONF = cfg.CONF
CONF.import_opt('backend',
                'bricks.openstack.common.db.api',
                group='database')

IMPL = utils.LazyPluggable(
    pivot='backend',
    config_group='database',
    sqlalchemy='bricks.db.sqlalchemy.migration')

INIT_VERSION = 0


def upgrade(version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.upgrade(version)


def downgrade(version=None):
    return IMPL.downgrade(version)


def version():
    return IMPL.version()


def stamp(version):
    return IMPL.stamp(version)


def revision(message, autogenerate):
    return IMPL.revision(message, autogenerate)
