import os
import logging
import shutil

from os import path

log = logging.getLogger(__name__)


def cast(val):
    """Attempt to coerce `val` into a numeric type, or a string stripped
    of whitespace.

    """

    for func in [int, float, lambda x: x.strip(), lambda x: x]:
        try:
            return func(val)
        except ValueError:
            pass


def mkdir(dirpath, clobber=False):
    """
    Create a (potentially existing) directory without errors. Raise
    OSError if directory can't be created. If clobber is True, remove
    dirpath if it exists.
    """

    if clobber:
        shutil.rmtree(dirpath, ignore_errors=True)

    try:
        os.mkdir(dirpath)
    except OSError:
        pass

    if not path.exists(dirpath):
        raise OSError('Failed to create %s' % dirpath)

    return dirpath
