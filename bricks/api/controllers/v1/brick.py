from datetime import datetime
import jsonpatch

import pecan
from pecan import rest

import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from bricks.api.controllers.v1 import base
from bricks.api.controllers.v1 import collection
from bricks.api.controllers.v1 import link
from bricks.api.controllers.v1 import types
from bricks.api.controllers.v1 import utils as api_utils
from bricks.common import exception
from bricks.common import policy
from bricks.common import states
from bricks import objects
from bricks.openstack.common import excutils
from bricks.openstack.common import log

LOG = log.getLogger(__name__)


def check_policy(context, action, target_obj=None):
    target = {
        'project_id': context.tenant,
        'user_id': context.user,
        'is_admin': context.is_admin,
    }
    target.update(target_obj or {})
    _action = 'brick:%s' % action
    policy.enforce(context, _action, target)


class BrickPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/configuration', ]


class BrickCommand(base.APIBase):
    type = wtypes.text
    data = {wtypes.text: wtypes.text}


class Brick(base.APIBase):
    """API representation of a Brick.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a brick.
    """

    uuid = types.uuid
    brickconfig_uuid = types.uuid
    deployed_at = datetime
    instance_id = wtypes.text
    tenant_id = wtypes.text
    status = wtypes.text
    configuration = {wtypes.text: wtypes.text}

    links = [link.Link]
    "A list containing a self link and associated brick links"

    def __init__(self, **kwargs):
        self.fields = objects.Brick.fields.keys()
        for k in self.fields:
            setattr(self, k, kwargs.get(k))

    @classmethod
    def convert_with_links(cls, rpc_brick, expand=True):
        brick = Brick(**rpc_brick.as_dict())

        if not expand:
            brick.unset_fields_except(['uuid', 'brickconfig_uuid',
                                       'deployed_at', 'instance_id',
                                       'status'])
        brick.links = [
            link.Link.make_link('self',
                                pecan.request.host_url,
                                'bricks', brick.uuid),
            link.Link.make_link('bookmark',
                                pecan.request.host_url,
                                'bricks', brick.uuid)
        ]
        return brick


class BricksCollection(collection.Collection):
    """API representation of a collection of Bricks."""

    bricks = [Brick]
    "A list containing Brick objects"

    def __init__(self, **kwargs):
        self._type = 'bricks'

    @classmethod
    def convert_with_links(cls, brick, limit, url=None,
                           expand=False, **kwargs):
        collection = BricksCollection()
        collection.bricks = [Brick.convert_with_links(br, expand)
                             for br in brick]
        url = url or None
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class BrickController(rest.RestController):
    """REST controller for Bricks."""

    _custom_actions = {
        'detail': ['GET'],
        'status_update': ['POST'],
    }

    def _get_brick_collection(self, tenant_id, brickconfig_uuid,
                              instance_id, status, marker, limit, sort_key,
                              sort_dir, expand=False, resource_url=None):

        filters = {}

        ctx = pecan.request.context

        ###
        # Tenant Filter Removed or Applied Here
        ###
        if not ctx.is_admin and not tenant_id == ctx.tenant_id:
            # only admins can set a non-tenant locked down tenant filter.
            raise exception.NotAuthorized()
        elif tenant_id:
            filters['tenant_id'] = tenant_id

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)
        marker_obj = None

        if marker:
            marker_obj = objects.Brick.get_by_uuid(pecan.request.context,
                                                   marker)
        if brickconfig_uuid:
            filters['brickconfig_uuid'] = brickconfig_uuid
        if instance_id:
            filters['instance_id'] = instance_id
        if status:
            filters['status'] = status

        bricks = pecan.request.dbapi.get_brick_list(
            filters, limit, marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return BricksCollection.convert_with_links(bricks, limit,
                                                   url=resource_url,
                                                   expand=expand,
                                                   sort_key=sort_key,
                                                   sort_dir=sort_dir)

    @wsme_pecan.wsexpose(BricksCollection, wtypes.text, types.uuid,
                         wtypes.text, wtypes.text, types.uuid, int,
                         wtypes.text, wtypes.text)
    def get_all(self, tenant_id=None, brickconfig_uuid=None,
                instance_id=None, status=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of bricks.

        :param tenant_id:
        :param brickconfig_uuid:
        :param instance_id:
        :param status:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        check_policy(pecan.request.context, 'get_all')
        return self._get_brick_collection(
            tenant_id, brickconfig_uuid, instance_id, status, marker, limit,
            sort_key, sort_dir)

    @wsme_pecan.wsexpose(BricksCollection, wtypes.text, types.uuid,
                         wtypes.text, wtypes.text, types.uuid, int,
                         wtypes.text, wtypes.text)
    def detail(self, tenant_id=None, brickconfig_uuid=None,
               instance_id=None, status=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of bricks with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        check_policy(pecan.request.context, 'get_all')
        # /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "bricks":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['bricks', 'detail'])
        return self._get_brick_collection(
            tenant_id, brickconfig_uuid, instance_id, status, marker,
            limit, sort_key, sort_dir, expand, resource_url)

    @wsme_pecan.wsexpose(Brick, types.uuid)
    def get_one(self, brick_uuid):
        """Retrieve information about the given brick.

        :param brick_uuid: UUID of a brick.
        """
        check_policy(pecan.request.context, 'get_one')
        req_ctx = pecan.request.context
        tenant_id = req_ctx.tenant_id if not req_ctx.is_admin else None
        rpc_brick = objects.Brick.get_by_uuid(pecan.request.context,
                                              brick_uuid, tenant_id=tenant_id)
        return Brick.convert_with_links(rpc_brick)

    @wsme_pecan.wsexpose(Brick, body=Brick, status_code=201)
    def post(self, brick):
        """Create a new brick.

        :param brick: a brick within the request body.
        """
        check_policy(pecan.request.context, 'create')
        try:
            new_brick = pecan.request.dbapi.create_brick(brick.as_dict())
            pecan.request.rpcapi.do_brick_deploy(pecan.request.context,
                                                 new_brick.uuid)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception(e)

        return Brick.convert_with_links(new_brick)

    @wsme.validate(types.uuid, [BrickPatchType])
    @wsme_pecan.wsexpose(Brick, types.uuid, body=[BrickPatchType])
    def patch(self, brick_uuid, patch):
        """Update an existing brick.

        :param brick_uuid: UUID of a brick.
        :param patch: a json PATCH document to apply to this brick.
        """
        check_policy(pecan.request.context, 'update')

        req_ctx = pecan.request.context
        tenant_id = req_ctx.tenant_id if not req_ctx.is_admin else None
        rpc_brick = objects.Brick.get_by_uuid(pecan.request.context,
                                              brick_uuid, tenant_id=tenant_id)
        try:
            brick = Brick(**jsonpatch.apply_patch(rpc_brick.as_dict(),
                                                  jsonpatch.JsonPatch(patch)))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Brick.fields:
            if rpc_brick[field] != getattr(brick, field):
                rpc_brick[field] = getattr(brick, field)

        rpc_brick.save()
        return Brick.convert_with_links(rpc_brick)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, brick_uuid):
        """Delete a brick.

        :param brick_uuid: UUID of a brick.
        """
        check_policy(pecan.request.context, 'delete')
        req_ctx = pecan.request.context
        tenant_id = req_ctx.tenant_id if not req_ctx.is_admin else None
        objects.Brick.get_by_uuid(pecan.request.context,
                                  brick_uuid, tenant_id=tenant_id)

        pecan.request.rpcapi.do_brick_destroy(pecan.request.context,
                                              brick_uuid)

    @wsme_pecan.wsexpose(Brick, types.uuid, body=BrickCommand)
    def status_update(self, brick_uuid, update):
        """Perform updates on a brick

        :param brick_uuid: UUID of a brick.
        :param update: json containing update data.
        """
        check_policy(pecan.request.context, 'status_update')
        if update.type == states.DEPLOYING:
            pecan.request.rpcapi.do_brick_deploying(pecan.request.context,
                                                    brick_uuid)
        elif update.type == states.DEPLOYFAIL:
            pecan.request.rpcapi.do_brick_deployfail(pecan.request.context,
                                                     brick_uuid)
        elif update.type == states.DEPLOYDONE:
            pecan.request.rpcapi.do_brick_deploydone(pecan.request.context,
                                                     brick_uuid)
