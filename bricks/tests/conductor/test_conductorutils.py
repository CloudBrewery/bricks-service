import mock

from bricks.conductor import utils
from bricks.db import api as dbapi
from bricks.openstack.common import context
from bricks.tests.db import base
from bricks.tests.db import utils as test_utils


class DeployTestCase(base.DbTestCase):

    def setUp(self):
        super(DeployTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class InitTestCase(base.DbTestCase):

    def setUp(self):
        super(InitTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class DestroyTestCase(base.DbTestCase):

    def setUp(self):
        super(DestroyTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class IPAssignTestCase(base.DbTestCase):

    def setUp(self):
        super(DestroyTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class NotificationTestCase(base.DbTestCase):
    def setUp(self):
        super(NotificationTestCase, self).setUp()
        self.dbapi = dbapi.get_instance()

        self.context.user = mock.Mock()
        self.context.user.username = "foouser@bar.com"
        self.context.auth_token = mock.Mock()
        self.context.auth_token.id = 'asdf'
        self.context.auth_token.tenant_id = 'asdf'

        self.test_brick = self.dbapi.create_brick(
            test_utils.get_test_brick())
        self.test_brick_config = self.dbapi.create_brickconfig(
            test_utils.get_test_brickconfig())

    @mock.patch('bricks.conductor.utils.send_admin_notification')
    @mock.patch('bricks.conductor.utils.send_installation_notification')
    def test_folks_notified(self, notify, send_admin):

        utils.notify_completion(self.context, self.test_brick,
                                self.test_brick_config)
        self.assertEqual(1, notify.call_count)
        self.assertEqual(1, send_admin.call_count)

    @mock.patch('emails.message.Message.send', autospec=True)
    def test_install_notification(self, send):

        def test_send(s, **kwargs):
            s.render_data = kwargs['render']
            self.assertTrue('you have a test' in s.text_body)

        send.side_effect = test_send

        utils.send_installation_notification(
            'admin@foo.com', self.test_brick, self.test_brick_config)
        self.assertEqual(1, send.call_count)

    @mock.patch('emails.message.Message.send', autospec=True)
    def test_notification_ports(self, send):

        self.test_brick_config.ports = [80, 443]
        self.test_brick_config.email_template = """
        Ports: {% for port in config.ports %}{{ port }} {% endfor %}
        """

        def test_send(s, **kwargs):
            s.render_data = kwargs['render']
            self.assertTrue('Ports: 80 443' in s.text_body)
        send.side_effect = test_send

        utils.send_installation_notification(
            'admin@foo.com', self.test_brick, self.test_brick_config)
        self.assertEqual(1, send.call_count)
