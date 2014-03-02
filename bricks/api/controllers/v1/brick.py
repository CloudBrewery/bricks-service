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
from bricks import objects
from bricks.openstack.common import excutils
from bricks.openstack.common import log

LOG = log.getLogger(__name__)


class BrickPatchType(types.JsonPatchType):
    pass


class Brick(base.APIBase):
    """API representation of a Brick.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a brick.
    """

    uuid = types.uuid
    brickconfig_uuid = types.uuid
    deployed_at = wtypes.datetime
    instance_id = wtypes.text
    status = wtypes.text
    configuration = {wtypes.text: types.MultiType(wtypes.text)}

    links = [link.Link]
    "A list containing a self link and associated brick links"

    def __init__(self, **kwargs):
        self.fields = objects.Brick.fields.keys()
        for k in self.fields:
            setattr(self, k, kwargs.get(k))

    @classmethod
    def convert_with_links(cls, rpc_brick, expand=True):
        brick = Brick(**rpc_brick.as_dict())

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
    }

    def _get_brick_collection(self, brickconfig_uuid, instance_id, status,
                              marker, limit, sort_key, sort_dir,
                              expand=False, resource_url=None):
        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)
        marker_obj = None
        if marker:
            marker_obj = objects.Brick.get_by_uuid(pecan.request.context,
                                                   marker)
        filters = {}
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

    @wsme_pecan.wsexpose(BricksCollection, types.uuid, wtypes.text,
                         wtypes.text, types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, brickconfig_uuid=None, instance_id=None, status=None,
                marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of bricks.

        :param brickconfig_uuid:
        :param instance_id:
        :param status:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_brick_collection(brickconfig_uuid, instance_id,
                                          status, marker, limit, sort_key,
                                          sort_dir)

    @wsme_pecan.wsexpose(BricksCollection, types.uuid, int,
                         wtypes.text, wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of bricks with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "bricks":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['bricks', 'detail'])
        return self._get_brick_collection(marker, limit, sort_key, sort_dir,
                                          expand, resource_url)

    @wsme_pecan.wsexpose(Brick, types.uuid)
    def get_one(self, brick_uuid):
        """Retrieve information about the given brick.

        :param brick_uuid: UUID of a brick.
        """
        rpc_brick = objects.Brick.get_by_uuid(pecan.request.context,
                                              brick_uuid)
        return Brick.convert_with_links(rpc_brick)

    @wsme_pecan.wsexpose(Brick, body=Brick, status_code=201)
    def post(self, brick):
        """Create a new brick.

        :param brick: a brick within the request body.
        """
        try:
            new_brick = pecan.request.dbapi.create_brick(brick.as_dict())
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
        rpc_brick = objects.Brick.get_by_uuid(pecan.request.context,
                                              brick_uuid)
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
        pecan.request.dbapi.destroy_brick(brick_uuid)
