import os
import logging
import shutil
import xml.dom.minidom
from itertools import izip_longest, ifilterfalse
from functools import wraps

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


def check_types(**kwargs):
    """Decorator to enforce argument types for a function or class
    method. Decorator arguments define objects against which
    corresponding funcrion or method arguments wil be compared using
    isinstance; raises TypeError if types do not match.

    Example::

        @check_types(name=basestring, times=int)
        def hello(name, times=1):
            for i in range(times):
                print('hello {}'.format(name))

    """
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*_args, **_kwargs):
            argdict = dict(zip(func.func_code.co_varnames, _args), **_kwargs)
            for arg, obj in kwargs.items():
                if arg in argdict and not isinstance(argdict[arg], obj):
                    raise TypeError('"{}" must be an instance of {}'.format(arg, obj))

            return func(*_args, **_kwargs)
        return wrapper
    return actual_decorator


@check_types(current=set, desired=set)
def reconcile(current, desired):
    """Return sets (to_add, to_remove) indicating elements that should be
    added to or removed from ``current`` to produce ``desired``.

    """

    to_remove = current - desired
    to_add = desired - current

    return to_add, to_remove


def prettify(xmlstr):
    pretty = xml.dom.minidom.parseString(xmlstr).toprettyxml(indent="    ")
    return '\n'.join(line.rstrip() for line in pretty.splitlines() if line.strip())


@check_types(n=int, fill=bool)
def grouper(iterable, n, fill=False, fillvalue=None):
    """Collect data into fixed-length chunks or blocks. If ``fill`` is
    True, pad final block with ``fillvalue`` up to a length of ``n``.

    """

    args = [iter(iterable)] * n
    for chunk in izip_longest(fillvalue=fillvalue, *args):
        if fill:
            yield chunk
        else:
            yield tuple(ifilterfalse(lambda x: x is None, chunk))
