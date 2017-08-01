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
    environment variables (the command line has precedence). Returns
    tuple of paths (certfile, keyfile) with values of None if not
    found.

    """

    certfile = args.cert_file
    if certfile:
        log.info('argument --cert-file={}'.format(certfile))
    elif cert_var_name in os.environ:
        certfile = os.environ[cert_var_name]
        log.info('environment variable {}={}'.format(cert_var_name, certfile))

    keyfile = args.key_file
    if keyfile:
        log.info('argument --key-file={}'.format(keyfile))
    elif key_var_name in os.environ:
        keyfile = os.environ[key_var_name]
        log.info('environment variable {}={}'.format(key_var_name, keyfile))

    return certfile, keyfile
