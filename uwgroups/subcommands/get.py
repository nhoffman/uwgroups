"""Show the API response for information about a group
"""

import logging
import pprint
import sys

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile, environment=args.environment) as conn:
        if conn.group_exists(args.group_name):
            body = conn.get_group(args.group_name)
            pprint.pprint(body)
        else:
            sys.exit(f'group "{args.group_name}" does not exist')
