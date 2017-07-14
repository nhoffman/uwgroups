"""
Test utils module.
"""

import logging

from uwgroups.utils import opener

from __init__ import TestBase, get_testfile
log = logging.getLogger(__name__)


class TestOpener(TestBase):
    def setUp(self):
        with open(get_testfile('lorem.txt')) as f:
            self.firstline = f.next()

    def test01(self):
        for suffix in ['txt', 'gz', 'bz2']:
            fn = get_testfile('lorem.'+suffix)
            fobj = opener(fn)
            self.assertEqual(fobj.next(), self.firstline)

    def test02(self):
        for suffix in ['txt', 'gz', 'bz2']:
            fn = get_testfile('lorem.'+suffix)
            fobj = opener(fn, 'r')
            self.assertEqual(fobj.next(), self.firstline)
