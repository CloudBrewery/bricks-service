"""Policy Engine For Bricks."""

import os.path

from oslo.config import cfg

from bricks.common import exception
from bricks.common import utils
from bricks.openstack.common.gettextutils import _
from bricks.openstack.common import policy


policy_opts = [
    cfg.StrOpt('policy_file',
               default='policy.json',
               help=_('JSON file representing policy.')),
    cfg.StrOpt('policy_default_rule',
               default='default',
               help=_('Rule checked when requested rule is not found.')),
]

CONF = cfg.CONF
CONF.register_opts(policy_opts)

_POLICY_PATH = None
_POLICY_CACHE = {}


def reset():
    global _POLICY_PATH
    global _POLICY_CACHE
    _POLICY_PATH = None
    _POLICY_CACHE = {}
    policy.reset()


def init():
    global _POLICY_PATH
    global _POLICY_CACHE
    if not _POLICY_PATH:
        _POLICY_PATH = CONF.policy_file
        if not os.path.exists(_POLICY_PATH):
            _POLICY_PATH = CONF.find_file(_POLICY_PATH)
        if not _POLICY_PATH:
            raise exception.ConfigNotFound(path=CONF.policy_file)
    utils.read_cached_file(_POLICY_PATH, _POLICY_CACHE,
                           reload_func=_set_rules)


def _set_rules(data):
    default_rule = CONF.policy_default_rule
    policy.set_rules(policy.Rules.load_json(data, default_rule))
