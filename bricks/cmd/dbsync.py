# -*- encoding: utf-8 -*-
"""
Run storage database migration.
"""

import sys

from oslo.config import cfg

from bricks.common import service
from bricks.db import migration


CONF = cfg.CONF


class DBCommand(object):

    def upgrade(self):
        migration.upgrade(CONF.command.revision)

    def downgrade(self):
        migration.downgrade(CONF.command.revision)

    def revision(self):
        migration.revision(CONF.command.message, CONF.command.autogenerate)

    def stamp(self):
        migration.stamp(CONF.command.revision)

    def version(self):
        print(migration.version())


def add_command_parsers(subparsers):
    command_object = DBCommand()

    parser = subparsers.add_parser('upgrade')
    parser.set_defaults(func=command_object.upgrade)
    parser.add_argument('--revision', nargs='?')

    parser = subparsers.add_parser('downgrade')
    parser.set_defaults(func=command_object.downgrade)
    parser.add_argument('--revision', nargs='?')

    parser = subparsers.add_parser('stamp')
    parser.add_argument('--revision', nargs='?')
    parser.set_defaults(func=command_object.stamp)

    parser = subparsers.add_parser('revision')
    parser.add_argument('-m', '--message')
    parser.add_argument('--autogenerate', action='store_true')
    parser.set_defaults(func=command_object.revision)

    parser = subparsers.add_parser('version')
    parser.set_defaults(func=command_object.version)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    # this is hack to work with previous usage of bricks-dbsync
    # pls change it to bricks-dbsync upgrade
    valid_commands = set([
        'upgrade', 'downgrade', 'revision',
        'version', 'stamp'
    ])
    if not set(sys.argv) & valid_commands:
        sys.argv.append('upgrade')

    service.prepare_service(sys.argv)
    CONF.command.func()
