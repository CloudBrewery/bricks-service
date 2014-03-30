from bricks.objects import base
from bricks.objects import utils


class MortarTask(base.BricksObject):

    fields = {
        'instance_id': utils.str_or_none,
        'configuration': utils.dict_or_none,
    }
