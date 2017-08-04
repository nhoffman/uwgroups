"""
Test utils module.
"""

import logging

from uwgroups.utils import reconcile, grouper

from __init__ import TestBase
log = logging.getLogger(__name__)


class TestReconcile(TestBase):
    def test01(self):
        to_add, to_remove = reconcile(
            current=set(),
            desired=set())

        self.assertSetEqual(to_add, set())
        self.assertSetEqual(to_remove, set())

    def test02(self):
        to_add, to_remove = reconcile(
            current={'a', 'b', 'c'},
            desired={'a', 'b', 'c'})

        self.assertSetEqual(to_add, set())
        self.assertSetEqual(to_remove, set())

    def test03(self):
        to_add, to_remove = reconcile(
            current={'a', 'b', 'c'},
            desired={'a', 'b'})

        self.assertSetEqual(to_add, set())
        self.assertSetEqual(to_remove, {'c'})

    def test04(self):
        to_add, to_remove = reconcile(
            current={'a', 'b'},
            desired={'a', 'b', 'c'})

        self.assertSetEqual(to_add, {'c'})
        self.assertSetEqual(to_remove, set())

    def test05(self):
        to_add, to_remove = reconcile(
            current={'b', 'd'},
            desired={'a', 'b', 'c'})

        self.assertSetEqual(to_add, {'a', 'c'})
        self.assertSetEqual(to_remove, {'d'})

    def test06(self):
        self.assertRaises(TypeError, reconcile, set(), [])


class TestGrouper(TestBase):
    def test01(self):
        items = range(10)
        chunks = list(grouper(items, 4))
        self.assertEquals(chunks[-1], (8, 9))

    def test02(self):
        items = range(10)
        chunks = list(grouper(items, 4, fill=True))
        self.assertEquals(chunks[-1], (8, 9, None, None))
