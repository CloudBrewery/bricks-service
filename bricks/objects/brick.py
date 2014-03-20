from bricks.db import api as db_api
from bricks.objects import base
from bricks.objects import utils


class Brick(base.BricksObject):

    dbapi = db_api.get_instance()

    fields = {
        'id': int,

        'uuid': utils.str_or_none,
        'brickconfig_uuid': utils.str_or_none,

        'deployed_at': utils.datetime_or_str_or_none,
        'instance_id': utils.str_or_none,
        'tenant_id': utils.str_or_none,

        # One of states. in states
        'status': utils.str_or_none,

        'configuration': utils.dict_or_none,
        # {'flavour', 'keypair', 'network', ''}
        'deploy_log': utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(brick, db_brick):
        """Converts a database entity to a formal object."""

        for field in brick.fields:
            brick[field] = db_brick[field]

        brick.obj_reset_changes()
        return brick

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, tenant_id=None):
        """Find a brick based on uuid and return a Brick object.

        :param uuid: the uuid of a brick.
        :returns: a :class:`Brick` object.
        """
        db_brick = cls.dbapi.get_brick(uuid, tenant_id)
        return Brick._from_db_object(cls(), db_brick)

    @base.remotable
    def save(self, context):
        """Save updates to this Brick.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        brick before updates are made.

        :param context: Security context
        """
        updates = self.obj_get_changes()
        self.dbapi.update_brick(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context):
        current = self.__class__.get_by_uuid(context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
