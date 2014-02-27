# vim: tabstop=4 shiftwidth=4 softtabstop=4

from oslo.config import cfg

from bricks.common import paths
from bricks.openstack.common.db.sqlalchemy import session as db_session
from bricks.openstack.common import rpc
from bricks import version

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('$sqlite_db')


def parse_args(argv, default_config_files=None):
    db_session.set_defaults(sql_connection=_DEFAULT_SQL_CONNECTION,
                            sqlite_db='bricks.sqlite')
    rpc.set_defaults(control_exchange='bricks')
    cfg.CONF(argv[1:],
             project='bricks',
             version=version.version_string(),
             default_config_files=default_config_files)
