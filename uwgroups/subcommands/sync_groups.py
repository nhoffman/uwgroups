"""Syncronize group membership
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    pass


def action(args):
    group_name = 'u_labmed_removeme2'

    key, cert = find_credentials(args)

    members = ['ngh2', 'jerrydav', 'rclayton']

    with UWGroups(key, cert) as conn:
        conn.sync_members(group_name, members, dry_run=False)
