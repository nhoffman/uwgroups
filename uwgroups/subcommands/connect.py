"""Test a connection
"""

import logging

from uwgroups.api import UWGroups
from uwgroups.subcommands import find_credentials

log = logging.getLogger(__name__)


def build_parser(parser):
    pass


def action(args):
    key, cert = find_credentials(args)
    conn = UWGroups(key, cert)
