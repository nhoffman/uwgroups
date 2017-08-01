"""Syncronize group membership
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")
    parser.add_argument('-m', '--members', nargs='+', help="one or more uwnetids")
    parser.add_argument('-n', '--dry-run', action='store_true', default=False)


def action(args):
    certfile, keyfile = find_credentials(args)

    group_name = args.group_name
    members = args.members

    with UWGroups(certfile, keyfile) as conn:
        conn.sync_members(group_name, members, dry_run=args.dry_run)