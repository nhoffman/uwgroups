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
    """Tries to define key and cert files from environment variables and
    command line arguments (the latter has precedence). Returns tuple
    of paths (key, cert) with values of None if not found.

    """

    if key_var_name in os.environ:
        key = os.environ[key_var_name]
        log.info('using environment variable {}={}'.format(key_var_name, key))
    else:
        key = args.key_file
        log.info('using argument --key-file={}'.format(key_var_name, key))

    if cert_var_name in os.environ:
        cert = os.environ[cert_var_name]
        log.info('using environment variable {}={}'.format(cert_var_name, cert))
    else:
        cert = args.cert_file
        log.info('using argument --cert-file={}'.format(cert_var_name, cert))

    return key, cert
