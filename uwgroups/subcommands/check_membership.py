"""Check membership of a single user in a group
"""

import logging
import pprint
import sys
import argparse
import json

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('group_name', help="name of a group")
    parser.add_argument('member_ids', help="one or more netids", nargs='+')
    parser.add_argument('-o', '--outfile', help="[stdout]",
                        type=argparse.FileType('w'), default=sys.stdout)


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile, environment=args.environment) as conn:
        for member_id in args.member_ids:
            print(member_id, conn.is_member(args.group_name, member_id))
