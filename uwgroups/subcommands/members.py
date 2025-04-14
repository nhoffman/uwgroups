"""List group members
"""

import argparse
import logging
import sys

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")
    parser.add_argument('-o', '--outfile', help="[stdout]",
                        type=argparse.FileType('w'), default=sys.stdout)


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile, environment=args.environment) as conn:
        if conn.group_exists(args.group_name):
            members = conn.get_members(args.group_name)
            for m in sorted(members):
                args.outfile.write(f'{m}\n')
        else:
            sys.exit(f'group "{args.group_name}" does not exist')
