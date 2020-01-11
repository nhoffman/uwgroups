"""Create a group
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")
    parser.add_argument('--exchange', choices=['yes', 'no'], default='yes')


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile) as conn:
        conn.create_group(args.group_name)
        conn.set_affiliate(
            args.group_name, service='exchange', active=args.exchange == 'yes')
