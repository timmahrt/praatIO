import unittest

from praatio import textgrid
from praatio.utilities.constants import Interval, Point, POINT_TIER
from praatio.utilities import constants
from praatio.utilities import errors

from test.praatio_test_case import PraatioTestCase


def makePointTier(name="pitch_values", points=None, minT=0, maxT=5.0):
    if points is None:
        points = [Point(1.3, "55"), Point(3.7, "99")]
    return textgrid.PointTier(name, points, minT, maxT)


class PointTierTests(PraatioTestCase):
    def test_append_tier_with_mixed_type_throws_exception(self):
        pointTier = makePointTier()
        intervalTier = textgrid.IntervalTier(
            "words",
            [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")],
            minT=0,
            maxT=5.0,
        )
        with self.assertRaises(errors.ArgumentError) as _:
            pointTier.appendTier(intervalTier)

    def test_append_tier_with_point_tiers(self):
        pointTier = textgrid.PointTier(
            "pitch_values", [Point(1.3, "55"), Point(3.7, "99")], minT=0, maxT=5
        )
        pointTier2 = textgrid.PointTier(
            "new_pitch_values", [Point(4.2, "153"), Point(7.1, "89")], minT=0, maxT=10
        )
        sut = pointTier.appendTier(pointTier2)
        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(15, sut.maxTimestamp)
        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99"), Point(9.2, "153"), Point(12.1, "89")],
            sut.entryList,
        )
        self.assertEqual(POINT_TIER, sut.tierType)

    def test_find_with_point_tiers(self):
        sut = makePointTier(
            points=[
                Point(1, "hello"),
                Point(2.5, "the"),
                Point(3.5, "world"),
            ]
        )
        self.assertEqual([], sut.find("mage", substrMatchFlag=False, usingRE=False))
        self.assertEqual([1], sut.find("the", substrMatchFlag=False, usingRE=False))

        self.assertEqual([], sut.find("mage", substrMatchFlag=True, usingRE=False))
        self.assertEqual([0, 1], sut.find("he", substrMatchFlag=True, usingRE=False))

        self.assertEqual([], sut.find("mage", substrMatchFlag=False, usingRE=True))
        self.assertEqual([0, 1], sut.find("he", substrMatchFlag=False, usingRE=True))
        self.assertEqual(
            [0, 1, 2], sut.find("[eo]", substrMatchFlag=False, usingRE=True)
        )

    def test_point_tier_creation_with_no_times(self):
        with self.assertRaises(errors.TimelessTextgridTierException) as cm:
            textgrid.PointTier("pitch_values", [], None, None)

        self.assertEqual(
            "All textgrid tiers much have a min and max duration", str(cm.exception)
        )

    def test_crop_raises_error_if_crop_start_time_occurs_after_crop_end_time(self):
        sut = makePointTier()

        with self.assertRaises(errors.ArgumentError) as cm:
            sut.crop(2.1, 1.1, "lax", True)

        self.assertEqual(
            "Crop error: start time (2.1) must occur before end time (1.1)",
            str(cm.exception),
        )

    def test_crop_when_rebase_to_zero_is_true(self):
        pointTier = makePointTier(
            points=[
                Point(0.5, "12"),
                Point(1.3, "55"),
                Point(3.7, "99"),
                Point(4.5, "32"),
            ],
            minT=0,
            maxT=5,
        )
        sut = pointTier.crop(1.0, 3.8, rebaseToZero=True)
        expectedPointTier = makePointTier(
            points=[Point(0.3, "55"), Point(2.7, "99")],
            minT=0,
            maxT=2.8,
        )
        self.assertEqual(expectedPointTier, sut)

    def test_crop_when_rebase_to_zero_is_false(self):
        pointTier = makePointTier(
            points=[
                Point(0.5, "12"),
                Point(1.3, "55"),
                Point(3.7, "99"),
                Point(4.5, "32"),
            ],
            minT=0,
            maxT=5,
        )
        sut = pointTier.crop(1.0, 3.8, rebaseToZero=False)
        expectedPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99")],
            minT=1,
            maxT=3.8,
        )
        self.assertEqual(expectedPointTier, sut)

    def test_erase_region_when_do_shrink_is_true(self):
        pointTier = makePointTier(
            points=[
                Point(0.5, "12"),
                Point(1.3, "55"),
                Point(3.7, "99"),
                Point(4.5, "32"),
            ],
            minT=0,
            maxT=5,
        )
        sut = pointTier.eraseRegion(1.0, 2.1, doShrink=True)
        expectedPointTier = makePointTier(
            points=[Point(0.5, "12"), Point(2.6, "99"), Point(3.4, "32")],
            minT=0,
            maxT=3.9,
        )
        self.assertEqual(expectedPointTier, sut)

    def test_erase_region_when_do_shrink_is_false(self):
        pointTier = makePointTier(
            points=[
                Point(0.5, "12"),
                Point(1.3, "55"),
                Point(3.7, "99"),
                Point(4.5, "32"),
            ]
        )
        sut = pointTier.eraseRegion(1.0, 2.1, doShrink=False)
        expectedPointTier = makePointTier(
            points=[Point(0.5, "12"), Point(3.7, "99"), Point(4.5, "32")],
        )
        self.assertEqual(expectedPointTier, sut)

    def test_get_values_at_points_when_fuzzy_matching_is_false(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )
        dataList = [
            (0.9, 100, 55),
            (1.3, 34, 92),
            (1.5, 32, 15),
            (1.8, 21, 34),
            (4.5, 31, 2),
            (4.8, 99, 44),
        ]

        self.assertEqual(
            [(1.3, 34, 92), (), (4.5, 31, 2)],
            sut.getValuesAtPoints(dataList, fuzzyMatching=False),
        )

        dataList2 = [(0.9, 100), (1.3, 34), (1.5, 32), (1.8, 21)]
        self.assertEqual(
            [(1.3, 34), (), ()],
            sut.getValuesAtPoints(dataList2, fuzzyMatching=False),
        )

    def test_get_values_at_points_when_fuzzy_matching_is_true(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        dataList = [
            (0.9, 100, 55),
            (1.3, 34, 92),
            (1.5, 32, 15),
            (1.8, 21, 34),
            (4.5, 31, 2),
            (4.8, 99, 44),
        ]
        self.assertEqual(
            [(1.3, 34, 92), (4.5, 31, 2), (4.5, 31, 2)],
            sut.getValuesAtPoints(dataList, fuzzyMatching=True),
        )

        dataList2 = [(0.9, 100), (1.3, 34), (1.5, 32), (1.8, 21)]
        self.assertEqual(
            [(1.3, 34), (1.8, 21), (1.8, 21)],
            sut.getValuesAtPoints(dataList2, fuzzyMatching=True),
        )

    def test_insert_point_at_start_of_point_tier(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(Point(0.5, "21"))

        self.assertEqual(
            [Point(0.5, "21"), Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_point_at_middle_of_point_tier(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(Point(3.9, "21"))

        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99"), Point(3.9, "21"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_entry_works_with_points_tuples_or_lists(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(Point(3.9, "21"))
        sut.insertEntry((4.0, "23"))
        sut.insertEntry((4.1, "99"))

        self.assertEqual(
            [
                Point(1.3, "55"),
                Point(3.7, "99"),
                Point(3.9, "21"),
                Point(4.0, "23"),
                Point(4.1, "99"),
                Point(4.5, "32"),
            ],
            sut.entryList,
        )

    def test_insert_point_at_end_of_point_tier(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(Point(4.9, "21"))

        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32"), Point(4.9, "21")],
            sut.entryList,
        )

    def test_insert_point_when_collision_occurs(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        with self.assertRaises(errors.CollisionError) as _:
            sut.insertEntry(
                Point(3.7, "hello"),
                constants.ErrorReportingMode.ERROR,
                constants.ErrorReportingMode.SILENCE,
            )

    def test_insert_point_when_collision_occurs_and_merge(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(
            Point(3.7, "hello"),
            constants.IntervalCollision.MERGE,
            constants.ErrorReportingMode.SILENCE,
        )
        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99-hello"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_point_when_collision_occurs_and_replace(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut.insertEntry(
            Point(3.7, "hello"),
            constants.IntervalCollision.REPLACE,
            constants.ErrorReportingMode.SILENCE,
        )
        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "hello"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_edit_timestamps_throws_error_if_reporting_mode_is_invalid(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        with self.assertRaises(errors.WrongOption) as _:
            sut.editTimestamps(
                2.0,
                "cats",
            )

    def test_edit_timestamps_can_make_points_appear_later(self):
        originalPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut = originalPointTier.editTimestamps(0.4)

        expectedPointTier = makePointTier(
            points=[Point(1.7, "55"), Point(4.1, "99"), Point(4.9, "32")],
        )
        self.assertEqual(expectedPointTier, sut)

    def test_edit_timestamps_can_make_points_appear_earlier(self):
        originalPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut = originalPointTier.editTimestamps(-0.4)

        expectedPointTier = makePointTier(
            points=[Point(0.9, "55"), Point(3.3, "99"), Point(4.1, "32")],
        )
        self.assertEqual(expectedPointTier, sut)

    def test_edit_timestamp_can_raise_exception_when_reporting_mode_is_silence(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                -1.4,
                constants.ErrorReportingMode.ERROR,
            )
        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                1.4,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamp_can_exceed_maxtimestamp_when_reporting_mode_is_silence(
        self,
    ):
        originalPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            maxT=5,
        )

        sut = originalPointTier.editTimestamps(
            1.4, constants.ErrorReportingMode.SILENCE
        )
        expectedPointTier = makePointTier(
            points=[Point(2.7, "55"), Point(5.1, "99"), Point(5.9, "32")],
            maxT=5.9,
        )
        self.assertEqual(expectedPointTier, sut)

    def test_edit_timestamp_drops_points_that_are_moved_before_zero(self):
        originalPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        sut = originalPointTier.editTimestamps(
            -1.4, constants.ErrorReportingMode.SILENCE
        )
        expectedPointTier = makePointTier(
            points=[Point(2.3, "99"), Point(3.1, "32")],
        )
        self.assertEqual(expectedPointTier, sut)

    def test_insert_space(self):
        originalPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            maxT=5,
        )

        sut = originalPointTier.insertSpace(2.0, 1.1)
        predictedPointTier = makePointTier(
            points=[Point(1.3, "55"), Point(4.8, "99"), Point(5.6, "32")],
            maxT=6.1,
        )
        self.assertEqual(predictedPointTier, sut)

    def test_validate_throws_error_if_points_are_not_in_sequence(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
        )

        self.assertTrue(sut.validate())
        sut.entryList.append(Point(3.9, "21"))
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_throws_error_if_points_are_less_than_minimum_time(self):
        sut = makePointTier(
            points=[Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
        )

        self.assertTrue(sut.validate())
        sut.minTimestamp = 2.0
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        with self.assertRaises(errors.OutOfBounds) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_throws_error_if_points_are_more_than_maximum_time(self):
        sut = makePointTier(
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            maxT=5,
        )

        self.assertTrue(sut.validate())
        sut.maxTimestamp = 3.0
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        with self.assertRaises(errors.OutOfBounds) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)


if __name__ == "__main__":
    unittest.main()
