# -*- encoding: utf-8 -*-

"""SQLAlchemy storage backend."""

import collections
import datetime

from oslo.config import cfg
from sqlalchemy.orm.exc import NoResultFound

from bricks.common import exception
from bricks.common import states
from bricks.common import utils
from bricks.db import api
from bricks.db.sqlalchemy import models
from bricks import objects
from bricks.openstack.common.db import exception as db_exc
from bricks.openstack.common.db.sqlalchemy import session as db_session
from bricks.openstack.common.db.sqlalchemy import utils as db_utils
from bricks.openstack.common import log
from bricks.openstack.common import timeutils

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


def add_port_filter(query, value):
    """Adds a port-specific filter to a query.

    Filters results by address, if supplied value is a valid MAC
    address. Otherwise attempts to filter results by identity.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_valid_mac(value):
        return query.filter_by(address=value)
    else:
        return add_identity_filter(query, value)


def add_port_filter_by_node(query, value):
    if utils.is_int_like(value):
        return query.filter_by(node_id=value)
    else:
        query = query.join(models.Node,
                models.Port.node_id == models.Node.id)
        return query.filter(models.Node.uuid == value)


def add_node_filter_by_chassis(query, value):
    if utils.is_int_like(value):
        return query.filter_by(chassis_id=value)
    else:
        query = query.join(models.Chassis,
                models.Node.chassis_id == models.Chassis.id)
        return query.filter(models.Chassis.uuid == value)


def _check_port_change_forbidden(port, session):
    node_id = port['node_id']
    if node_id is not None:
        query = model_query(models.Node, session=session)
        query = query.filter_by(id=node_id)
        node_ref = query.one()
        if node_ref['reservation'] is not None:
            raise exception.NodeLocked(node=node_id,
                                       host=node_ref['reservation'])


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


def _check_node_already_locked(query, query_by):
    no_reserv = None
    locked_ref = query.filter(models.Node.reservation != no_reserv).first()
    if locked_ref:
        raise exception.NodeLocked(node=locked_ref[query_by],
                                   host=locked_ref['reservation'])


def _handle_node_lock_not_found(nodes, query, query_by):
    refs = query.all()
    existing = [ref[query_by] for ref in refs]
    missing = set(nodes) - set(existing)
    raise exception.NodeNotFound(node=missing.pop())


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_nodes_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'chassis_uuid' in filters:
            # get_chassis() to raise an exception if the chassis is not found
            chassis_obj = self.get_chassis(filters['chassis_uuid'])
            query = query.filter_by(chassis_id=chassis_obj.id)
        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Node.instance_uuid != None)
            else:
                query = query.filter(models.Node.instance_uuid == None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Node.reservation != None)
            else:
                query = query.filter(models.Node.reservation == None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])

        return query

    def get_nodeinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Node.id]
        else:
            columns = [getattr(models.Node, c) for c in columns]

        query = model_query(*columns, base_model=models.Node)
        query = self._add_nodes_filters(query, filters)
        return _paginate_query(models.Node, limit, marker,
                               sort_key, sort_dir, query)
