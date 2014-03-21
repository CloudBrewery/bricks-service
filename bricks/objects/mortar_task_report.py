from bricks.objects import base
from bricks.objects import utils


class MortarTaskReport(base.BricksObject):

    fields = {
        'instance_id': utils.str_or_none,
        'test_result': bool,
        'message': utils.str_or_none,
    }
