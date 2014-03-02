import datetime


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


class BrickConfigPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/name', '/version', 'tenant_id']


class BrickConfig(base.APIBase):
    """API representation of a brickconfig.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    brickconfig.
    """

    uuid = types.uuid
    name = wtypes.text
    version = wtypes.text
    is_public = types.boolean
    tenant_id = wtypes.text
    tag = wtypes.text
    description = wtypes.text
    logo = wtypes.text
    app_version = wtypes.text
    ports = [wtypes.text]
    environ = [wtypes.text]
    email_template = wtypes.text

    links = [link.Link]

    def __init__(self, **kwargs):
        self.fields = objects.BrickConfig.fields.keys()
        for k in self.fields:
            setattr(self, k, kwargs.get(k))

    @classmethod
    def convert_with_links(cls, rpc_brickconfig, expand=True):
        brickconfig = BrickConfig(**rpc_brickconfig.as_dict())
        if not expand:
            brickconfig.unset_fields_except(['uuid', 'address'])

        # never expose the node_id attribute
        brickconfig.node_id = wtypes.Unset

        brickconfig.links = [
            link.Link.make_link('self', pecan.request.host_url,
                                'brickconfigs', brickconfig.uuid),
            link.Link.make_link('bookmark', pecan.request.host_url,
                                'brickconfigs', brickconfig.uuid,
                                bookmark=True)
        ]
        return brickconfig

    @classmethod
    def sample(cls):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     address='fe:54:00:77:07:d9',
                     extra={'foo': 'bar'},
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
        # NOTE(lucasagomes): node_uuid getter() method look at the
        # _node_uuid variable
        sample._node_uuid = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        return sample


class BrickConfigCollection(collection.Collection):
    """API representation of a collection of BrickConfigs."""

    brickconfigs = [BrickConfig]
    "A list containing ports objects"

    def __init__(self, **kwargs):
        self._type = 'brickconfigs'

    @classmethod
    def convert_with_links(cls, rpc_brickconfigs, limit, url=None,
                           expand=False, **kwargs):
        collection = BrickConfigCollection()
        collection.brickconfigs = [BrickConfig.convert_with_links(bc, expand)
                                   for bc in rpc_brickconfigs]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.brickconfigs = [BrickConfig.sample()]
        return sample


class BrickConfigController(rest.RestController):
    """REST controller for BrickConfigs."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def __init__(self, from_nodes=False):
        self._from_nodes = from_nodes

    def _get_brickconfigs_collection(self, tag, is_public, marker, limit,
                                     sort_key, sort_dir, expand=False,
                                     resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.BrickConfig.get_by_uuid(
                pecan.request.context, marker)

        filters = {}
        if tag:
            filters['tag'] = tag
        if is_public:
            filters['is_public'] = is_public

        brickconfigs = pecan.request.dbapi.get_brickconfig_list(
            filters, limit, marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return BrickConfigCollection.convert_with_links(
            brickconfigs, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

    @wsme_pecan.wsexpose(BrickConfigCollection, wtypes.text, types.boolean,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, tag=None, is_public=None, marker=None,
                limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of brickconfigs.

        :param tag:
        :param is_public:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_brickconfigs_collection(tag, is_public, marker,
                                                 limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(BrickConfigCollection, wtypes.text, types.boolean,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, tag=None, is_public=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of brickconfigs with detail.

        :param tag:
        :param is_public:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "brickconfigs":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['brickconfigs', 'detail'])
        return self._get_brickconfigs_collection(tag, is_public, marker,
                                                 limit, sort_key, sort_dir,
                                                 expand, resource_url)

    @wsme_pecan.wsexpose(BrickConfig, types.uuid)
    def get_one(self, brickconfig_uuid):
        """Retrieve information about the given bc.

        :param brickconfig_uuid: UUID of a bc.
        """
        if self._from_nodes:
            raise exception.OperationNotPermitted

        rpc_brickconfig = objects.BrickConfig.get_by_uuid(
            pecan.request.context, brickconfig_uuid)
        return BrickConfig.convert_with_links(rpc_brickconfig)

    @wsme_pecan.wsexpose(BrickConfig, body=BrickConfig, status_code=201)
    def post(self, brickconfig):
        """Create a new bc.

        :param brickconfig: a bc within the request body.
        """
        if self._from_nodes:
            raise exception.OperationNotPermitted

        try:
            new_bc = pecan.request.dbapi.create_brickconfig(
                brickconfig.as_dict())
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception(e)
        return BrickConfig.convert_with_links(new_bc)

    @wsme.validate(types.uuid, [BrickConfigPatchType])
    @wsme_pecan.wsexpose(BrickConfig, types.uuid, body=[BrickConfigPatchType])
    def patch(self, brickconfig_uuid, patch):
        """Update an existing bc.

        :param brickconfig_uuid: UUID of a bc.
        :param patch: a json PATCH document to apply to this bc.
        """
        if self._from_nodes:
            raise exception.OperationNotPermitted

        rpc_brickconfig = objects.BrickConfig.get_by_uuid(
            pecan.request.context, brickconfig_uuid)
        try:
            bc = BrickConfig(**jsonpatch.apply_patch(
                rpc_brickconfig.as_dict(), jsonpatch.JsonPatch(patch)))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.BrickConfig.fields:
            if rpc_brickconfig[field] != getattr(bc, field):
                rpc_brickconfig[field] = getattr(bc, field)

        rpc_brickconfig.save()
        return BrickConfig.convert_with_links(rpc_brickconfig)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, brickconfig_uuid):
        """Delete a bc.

        :param brickconfig_uuid: UUID of a bc.
        """
        if self._from_nodes:
            raise exception.OperationNotPermitted

        pecan.request.dbapi.destroy_brickconfig(brickconfig_uuid)
