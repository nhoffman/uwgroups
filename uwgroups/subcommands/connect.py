"""Create a connection - useful mainly for testing credentials
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    pass


def action(args):
    key, cert = find_credentials(args)
    conn = UWGroups(key, cert)

    for attr in ['host', 'port', 'key_file', 'cert_file']:
        print('{}: {}'.format(attr, getattr(conn.connection, attr)))

    print('admin users defined by cert: {}'.format(conn.admins))

    print 'ok'
