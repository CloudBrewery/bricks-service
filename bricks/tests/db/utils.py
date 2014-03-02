"""Bricks test utilities."""

import datetime
from bricks.common import states


def get_test_brick(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', 'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'brickconfig_uuid': kw.get('brickconfig_uuid',
                                   '1be26c0b-03f2-4d2e-ae87-c02d7f33c123'),

        'deployed_at': kw.get('deployed_at', datetime.datetime.now()),
        'instance_id': kw.get('instance_id',
                              '1be26c0b-03f2-4d2e-ae87-c02d7f33c781'),
        'status': kw.get('status', states.NOSTATE),
        'configuration': kw.get('configuration', {}),
        'deploy_log': kw.get('deploy_log', 'this\nis\na\ntest\n'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def get_test_brickconfig(**kw):
    return {
        'id': kw.get('id', 133),
        'uuid': kw.get('uuid',
                       '1be26c0b-03f2-4d2e-ae87-c02d7f33c123'),
        'name': kw.get('name', 'abrickconfig'),
        'version': kw.get('version', 'v0.0'),
        'is_public': kw.get('is_public', False),
        'tenant_id': kw.get('tenant_id', 'iamatenant'),

        'tag': kw.get('tag', 'testapp'),
        'description': kw.get('description', 'i am a test app'),
        'logo': kw.get('logo', 'https://gravatar.com/logo.png'),
        'app_version': kw.get('app_version', '10.2.9'),

        'ports': kw.get('ports', []),
        'environ': kw.get('environ', []),
        'email_template': kw.get('environ', 'you have a brick now.. grats.'),

        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),

    }
