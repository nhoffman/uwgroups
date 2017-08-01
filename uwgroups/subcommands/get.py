"""Get xml representation of a group
"""

import logging


from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile) as conn:
        body = conn.get_group(args.group_name)
        print(body)
