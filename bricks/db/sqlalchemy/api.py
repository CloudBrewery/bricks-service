# -*- encoding: utf-8 -*-

"""SQLAlchemy storage backend."""

from oslo.config import cfg
from sqlalchemy.orm.exc import NoResultFound

from bricks.common import exception
from bricks.common import utils
from bricks.common import states
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


def _check_brickconfig_in_use(brickconfig, session):
    brickconfig_uuid = brickconfig['uuid']
    if brickconfig_uuid is not None:
        query = model_query(models.Brick, session=session)
        query = query.filter_by(brickconfig_uuid=brickconfig_uuid)

        try:
            brick_ref = query.one()
            raise exception.BrickConfigInUse(brick=brick_ref)
        except NoResultFound:
            pass


from bricks.db import api


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_brick_filters(self, query, filters):
        if filters is None:
            filters = {}

        if 'brickconfig_uuid' in filters:
            query = query.filter_by(
                brickconfig_uuid=filters['brickconfig_uuid'])
        if 'instance_id' in filters:
            query = query.filter_by(instance_id=filters['instance_id'])
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        if 'tenant_id' in filters:
            query = query.filter_by(tenant_id=filters['tenant_id'])

        return query

    def _add_brickconfig_filters(self, query, filters):
        if filters is None:
            filters = {}

        if 'tag' in filters:
            query = query.filter_by(tag=filters['tag'])
        if 'is_public' in filters:
            query = query.filter_by(is_public=filters['is_public'])
        if 'tenant_id' in filters:
            query = query.filter_by(tenant_id=filters['tenant_id'])

        return query

    @objects.objectify(objects.Brick)
    def get_brick_list(self, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Brick)
        query = self._add_brick_filters(query, filters)
        return _paginate_query(models.Brick, limit, marker,
                               sort_key, sort_dir, query)

    @objects.objectify(objects.Brick)
    def create_brick(self, values):
        # ensure defaults are present for new bricks
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()
        if not values.get('status'):
            values['status'] = states.NOSTATE

        brick = models.Brick()
        brick.update(values)
        brick.save()
        return brick

    @objects.objectify(objects.Brick)
    def get_brick(self, brick_id, tenant_id=None):
        query = model_query(models.Brick)
        query = add_identity_filter(query, brick_id)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        try:
            return query.one()
        except NoResultFound:
            raise exception.BrickNotFound(brick=brick_id)

    @objects.objectify(objects.Brick)
    def update_brick(self, brick_id, values, tenant_id=None):
        session = get_session()
        with session.begin():
            query = model_query(models.Brick, session=session)
            query = add_identity_filter(query, brick_id)
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)

            count = query.update(values)
            if count != 1:
                raise exception.BrickNotFound(brick=brick_id)
            ref = query.one()
        return ref

    def destroy_brick(self, brick_id, tenant_id=None):
        session = get_session()
        with session.begin():
            query = model_query(models.Brick, session=session)
            query = add_identity_filter(query, brick_id)

            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)

            try:
                ref = query.one()
            except NoResultFound:
                raise exception.BrickNotFound(brick=brick_id)

            query.delete()

    @objects.objectify(objects.BrickConfig)
    def get_brickconfig_list(self, filters=None, limit=None, marker=None,
                             sort_key=None, sort_dir=None):
        query = model_query(models.BrickConfig)
        query = self._add_brickconfig_filters(query, filters)
        return _paginate_query(models.BrickConfig, limit, marker, sort_key,
                               sort_dir, query)

    @objects.objectify(objects.BrickConfig)
    def create_brickconfig(self, values):
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()
        if not values.get('version'):
            values['version'] = '1.0'

        bc = models.BrickConfig()
        bc.update(values)
        bc.save()
        return bc

    @objects.objectify(objects.BrickConfig)
    def get_brickconfig(self, brickconfig_id):
        query = model_query(models.BrickConfig)
        query = add_identity_filter(query, brickconfig_id)

        try:
            return query.one()
        except NoResultFound:
            raise exception.BrickConfigNotFound(brickconfig=brickconfig_id)

    @objects.objectify(objects.BrickConfig)
    def update_brickconfig(self, brickconfig_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.BrickConfig, session=session)
            query = add_identity_filter(query, brickconfig_id)

            count = query.update(values)
            if count != 1:
                raise exception.BrickConfigNotFound(brickconfig=brickconfig_id)
            ref = query.one()
        return ref

    def destroy_brickconfig(self, brickconfig_id):
        session = get_session()
        with session.begin():
            query = model_query(models.BrickConfig, session=session)
            query = add_identity_filter(query, brickconfig_id)

            try:
                ref = query.one()
            except NoResultFound:
                raise exception.BrickConfigNotFound(brickconfig=brickconfig_id)

            _check_brickconfig_in_use(ref, session)

            query.delete()


