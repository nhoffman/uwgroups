"""Syncronize group membership, creating groups if necessary
"""


import argparse
import logging
import json

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('groupfile', type=argparse.FileType(),
                        help='json file containing a mapping of {group: [netids]}')
    parser.add_argument('-n', '--dry-run', action='store_true', default=False)


def action(args):
    certfile, keyfile = find_credentials(args)
    groupdict = json.load(args.groupfile)

    with UWGroups(certfile, keyfile, environment=args.environment) as conn:
        for group_name, members in sorted(groupdict.items()):
            conn.sync_members(group_name, members, dry_run=args.dry_run)
