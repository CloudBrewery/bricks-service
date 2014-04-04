from bricks.objects import base
from bricks.objects import utils


COMPLETE = 'TASK-COMPLETE'
ERROR = 'TASK-ERROR'
RUNNING = 'TASK-RUNNING'
INSUFF = 'INSUFFICIENT-DATA'
STATE_LIST = [COMPLETE, ERROR, RUNNING, INSUFF]


class MortarTask(base.BricksObject):

    fields = {
        'instance_id': utils.str_or_none,
        'configuration': utils.dict_or_none,
    }
