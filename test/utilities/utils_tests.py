import unittest

from praatio.utilities import utils
from praatio.utilities import errors


class UtilsTests(unittest.TestCase):
    def test_interval_overlap_check_using_time_threshold_flag(self):
        self.assertTrue(utils.intervalOverlapCheck([0, 5], [2, 7]))
        self.assertTrue(utils.intervalOverlapCheck([0, 5], [2, 7], timeThreshold=3))
        self.assertFalse(utils.intervalOverlapCheck([0, 5], [2, 7], timeThreshold=4))

    def test_interval_overlap_check_using_precent_threshold_flag(self):
        self.assertTrue(utils.intervalOverlapCheck([0, 100], [50, 100]))
        self.assertTrue(
            utils.intervalOverlapCheck([0, 100], [50, 100], percentThreshold=0.5)
        )
        self.assertFalse(
            utils.intervalOverlapCheck([0, 100], [50, 100], percentThreshold=0.6)
        )

        self.assertTrue(utils.intervalOverlapCheck([0, 6], [2, 8]))
        self.assertTrue(
            utils.intervalOverlapCheck([0, 6], [2, 8], percentThreshold=0.5)
        )
        self.assertFalse(
            utils.intervalOverlapCheck([0, 6], [2, 8], percentThreshold=0.6)
        )

    def test_interval_overlap_check_using_boundary_inclusive_flag(self):
        self.assertFalse(utils.intervalOverlapCheck([0, 5], [5, 7]))

        self.assertFalse(
            utils.intervalOverlapCheck([0, 5], [5, 7], boundaryInclusive=False)
        )
        self.assertTrue(
            utils.intervalOverlapCheck([0, 5], [5, 7], boundaryInclusive=True)
        )

    def test_safe_zip(self):
        listToZip = [[1, 2, 3], [4, 5, 6, 7]]

        self.assertRaises(errors.SafeZipException, utils.safeZip, listToZip, True)

        expectedZippedResult = [(1, 4), (2, 5), (3, 6), (None, 7)]
        self.assertEqual(expectedZippedResult, list(utils.safeZip(listToZip, False)))


if __name__ == "__main__":
    unittest.main()
