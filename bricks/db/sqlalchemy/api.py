# -*- encoding: utf-8 -*-

"""SQLAlchemy storage backend."""

from oslo.config import cfg

from bricks.common import exception
from bricks.common import utils
from bricks import objects

from bricks.db.sqlalchemy import models
from bricks.openstack.common.db.sqlalchemy import session as db_session
from bricks.openstack.common.db.sqlalchemy import utils as db_utils
from bricks.openstack.common import log

CONF = cfg.CONF
CONF.import_opt('connection',
                'bricks.openstack.common.db.sqlalchemy.session',
                group='database')
CONF.import_opt('heartbeat_timeout',
                'bricks.conductor.manager',
                group='conductor')

LOG = log.getLogger(__name__)

get_engine = db_session.get_engine
get_session = db_session.get_session


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value):
        return query.filter_by(id=value)
    elif utils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def add_filter_by_many_identities(query, model, values):
    """Adds an identity filter to a query for values list.

    Filters results by ID, if supplied values contain a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param model: Model for filter.
    :param values: Values for filtering results by.
    :return: tuple (Modified query, filter field name).
    """
    if not values:
        raise exception.InvalidIdentity(identity=values)
    value = values[0]
    if utils.is_int_like(value):
        return query.filter(getattr(model, 'id').in_(values)), 'id'
    elif utils.is_uuid_like(value):
        return query.filter(getattr(model, 'uuid').in_(values)), 'uuid'
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(query, model, limit, sort_keys,
                                    marker=marker, sort_dir=sort_dir)
    return query.all()


from bricks.db import api
class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_brick_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'brickconfig_uuid' in filters:
            query = query.filter_by(brickconfig_uuid=filters['brickconfig_uuid'])
        if 'instance_id' in filters:
            query = query.filter_by(instance_id=filters['instance_id'])
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])

        return query

    @objects.objectify(objects.Brick)
    def get_brick_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        import pdb; pdb.set_trace()
        query = model_query(models.Brick)
        query = self._add_brick_filters(query, filters)
        return _paginate_query(models.Brick, limit, marker,
                               sort_key, sort_dir, query)


