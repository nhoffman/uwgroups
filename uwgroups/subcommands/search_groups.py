"""List groups matching a pattern
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('name')


def action(args):
    certfile, keyfile = find_credentials(args)
    with UWGroups(certfile, keyfile, environment=args.environment) as conn:
        groups = conn.search_groups(args.name)
        for group in groups:
            print(group)
