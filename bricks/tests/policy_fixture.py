import os

import fixtures
from oslo.config import cfg

from bricks.common import policy as bricks_policy
from bricks.openstack.common import policy as common_policy
from bricks.tests import fake_policy

CONF = cfg.CONF


class PolicyFixture(fixtures.Fixture):

    def setUp(self):
        super(PolicyFixture, self).setUp()
        self.policy_dir = self.useFixture(fixtures.TempDir())
        self.policy_file_name = os.path.join(self.policy_dir.path,
                                             'policy.json')
        with open(self.policy_file_name, 'w') as policy_file:
            policy_file.write(fake_policy.policy_data)
        CONF.set_override('policy_file', self.policy_file_name)
        bricks_policy.reset()
        bricks_policy.init()
        self.addCleanup(bricks_policy.reset)

    def set_rules(self, rules):
        common_policy.set_rules(common_policy.Rules(
            dict((k, common_policy.parse_rule(v))
                 for k, v in rules.items())))
