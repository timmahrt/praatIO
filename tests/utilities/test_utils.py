import unittest

from praatio.utilities import utils
from praatio.utilities import errors


class TestUtils(unittest.TestCase):
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

    def test_sign(self):
        self.assertEqual(-1, utils.sign(-1))
        self.assertEqual(0, utils.sign(0))
        self.assertEqual(1, utils.sign(1))
        self.assertEqual(1, utils.sign(100.5))

    def test_invert_interval_list_throws_exception_if_intervals_are_malformed(self):
        with self.assertRaises(errors.ArgumentError) as _:
            utils.invertIntervalList([[19, 30], [70, 44]])

    def test_invert_interval_list(self):
        sut = [(5, 10), (15, 21.5), (32.1, 40)]
        expected_output = [(10, 15), (21.5, 32.1)]
        self.assertEqual(expected_output, utils.invertIntervalList(sut))

    def test_invert_interval_list_with_min_value(self):
        sut = [(5, 10), (15, 21.5), (32.1, 40)]
        expected_output = [(1, 5), (10, 15), (21.5, 32.1)]
        self.assertEqual(expected_output, utils.invertIntervalList(sut, minValue=1))

    def test_invert_interval_list_with_max_value(self):
        sut = [(5, 10), (15, 21.5), (32.1, 40)]
        expected_output = [(10, 15), (21.5, 32.1), (40, 100)]
        self.assertEqual(expected_output, utils.invertIntervalList(sut, maxValue=100))

    def test_invert_when_interval_list_is_empty(self):
        self.assertEqual([], utils.invertIntervalList([]))
        self.assertEqual(
            [(1, 99)], utils.invertIntervalList([], minValue=1, maxValue=99)
        )

    def test_safe_zip(self):
        listToZip = [[1, 2, 3], [4, 5, 6, 7]]

        with self.assertRaises(errors.SafeZipException) as _:
            utils.safeZip(listToZip, True)

        expectedZippedResult = [(1, 4), (2, 5), (3, 6), (None, 7)]
        self.assertEqual(expectedZippedResult, list(utils.safeZip(listToZip, False)))

    def test_choose_closest_time(self):
        # Prefers not-None candidate
        self.assertEqual(5, utils.chooseClosestTime(6, 5, None))
        self.assertEqual(5, utils.chooseClosestTime(6, None, 5))

        # Ok with duplicate candidates
        self.assertEqual(5, utils.chooseClosestTime(6, 5, 5))

        # Prefers the first candidate if the two are equidistant
        self.assertEqual(5, utils.chooseClosestTime(6, 5, 7))
        self.assertEqual(7, utils.chooseClosestTime(6, 7, 5))

        # Chooses the closest candidate, order doesn't matter
        self.assertEqual(5, utils.chooseClosestTime(6, 5, 8))
        self.assertEqual(5, utils.chooseClosestTime(6, 8, 5))

        # Must submit at least one candidate
        with self.assertRaises(errors.ArgumentError) as _:
            utils.chooseClosestTime(6, None, None)


if __name__ == "__main__":
    unittest.main()
