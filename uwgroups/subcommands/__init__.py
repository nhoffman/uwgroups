import glob
import logging
import os
from os.path import splitext, split, join

from uwgroups import cert_var_name, key_var_name

log = logging.getLogger(__name__)


def itermodules(subcommands_path, root=__name__):

    commands = [x for x in [splitext(split(p)[1])[0]
                            for p in glob.glob(join(subcommands_path, '*.py'))]
                if not x.startswith('_')]

    for command in commands:
        yield command, __import__('%s.%s' % (root, command), fromlist=[command])


def find_credentials(args):
    """Defines key and cert files from command line arguments or
    environment variables (the former has precedence). Returns tuple
    of paths (key, cert) with values of None if not found.

    """

    key = args.key_file
    if key:
        log.info('argument --key-file={}'.format(key))
    elif key_var_name in os.environ:
        key = os.environ[key_var_name]
        log.info('environment variable {}={}'.format(key_var_name, key))
    else:
        log.warning(
            'no key file specified using either --key-file or {}'.format(key_var_name))

    cert = args.cert_file
    if cert:
        log.info('argument --cert-file={}'.format(cert))
    elif cert_var_name in os.environ:
        cert = os.environ[cert_var_name]
        log.info('environment variable {}={}'.format(cert_var_name, cert))
    else:
        log.warning(
            'no cert file specified using either --cert-file or {}'.format(
                cert_var_name))

    return key, cert
