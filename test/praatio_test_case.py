import unittest
import os


class PraatioTestCase(unittest.TestCase):
    def __init__(self, *args, **kargs):
        super(PraatioTestCase, self).__init__(*args, **kargs)

        root = os.path.dirname(os.path.realpath(__file__))
        self.dataRoot = os.path.join(root, "files")
        self.outputRoot = os.path.join(self.dataRoot, "io_test_output")

    def assertAllAlmostEqual(self, listA, listB):
        for valA, valB in zip(listA, listB):
            self.assertAlmostEqual(valA, valB)
