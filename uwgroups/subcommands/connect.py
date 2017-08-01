"""Create a connection - useful mainly for testing credentials
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    pass


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile) as conn:
        for attr in ['host', 'port']:
            print('{}: {}'.format(attr, getattr(conn.connection, attr)))
        for attr in ['certfile', 'keyfile']:
            print('{}: {}'.format(attr, getattr(conn, attr)))

        print('admin users defined by cert: {}'.format(conn.admins))

        print 'ok'
