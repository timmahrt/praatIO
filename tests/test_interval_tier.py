import unittest
from os.path import join

from praatio import textgrid
from praatio.utilities.constants import Interval, INTERVAL_TIER, Point
from praatio.utilities import errors
from praatio.utilities import constants

from tests.praatio_test_case import PraatioTestCase
from tests import testing_utils
from tests.testing_utils import makeIntervalTier, makePointTier


class TestIntervalTier(PraatioTestCase):
    def test__eq__(self):
        sut = makeIntervalTier(name="foo", intervals=[], minT=1.0, maxT=4.0)
        intervalTier = makeIntervalTier(name="foo", intervals=[], minT=1.0, maxT=4.0)
        pointTier = makePointTier()
        interval1 = Interval(1.0, 2.0, "hello")
        interval2 = Interval(2.0, 3.0, "world")

        # must be the same type
        self.assertEqual(sut, intervalTier)
        self.assertNotEqual(sut, pointTier)

        # must have the same entries
        sut.insertEntry(interval1)
        self.assertNotEqual(sut, intervalTier)

        # just having the same number of entries is not enough
        intervalTier.insertEntry(interval2)
        self.assertNotEqual(sut, intervalTier)

        sut.insertEntry(interval2)
        intervalTier.insertEntry(interval1)
        self.assertEqual(sut, intervalTier)

        # must have the same name
        intervalTier.name = "bar"
        self.assertNotEqual(sut, intervalTier)
        intervalTier.name = "foo"
        self.assertEqual(sut, intervalTier)

        # must have the same min/max timestamps
        intervalTier.minTimestamp = 0.5
        self.assertNotEqual(sut, intervalTier)

        intervalTier.minTimestamp = 1
        intervalTier.maxTimestamp = 5
        self.assertNotEqual(sut, intervalTier)

        sut.maxTimestamp = 5
        self.assertEqual(sut, intervalTier)

    def test__len__returns_the_number_of_intervals_in_the_interval_tier(self):
        interval1 = Interval(1.0, 2.0, "hello")
        interval2 = Interval(2.0, 3.0, "world")

        sut = makeIntervalTier(intervals=[])

        self.assertEqual(len(sut), 0)

        sut.insertEntry(interval1)
        self.assertEqual(len(sut), 1)

        sut.insertEntry(interval2)
        self.assertEqual(len(sut), 2)

        sut.deleteEntry(interval1)
        self.assertEqual(len(sut), 1)

        sut.deleteEntry(interval2)
        self.assertEqual(len(sut), 0)

    def test__iter__iterates_through_intervals_in_the_interval_tier(self):
        interval1 = Interval(1.0, 2.0, "hello")
        interval2 = Interval(2.0, 3.0, "world")

        sut = makeIntervalTier(intervals=[interval1, interval2])

        seenIntervals = []
        for interval in sut:
            seenIntervals.append(interval)

        self.assertEqual(seenIntervals, [interval1, interval2])

    def test_inequivalence_with_non_interval_tiers(self):
        sut = makeIntervalTier()
        self.assertNotEqual(sut, 55)

    def test_creating_an_interval_tier_with_invalid_intervals_raises_an_error(self):
        with self.assertRaises(errors.TextgridStateError) as _:
            textgrid.IntervalTier(
                "words",
                [Interval(2.0, 1.0, "hello world")],
            )

    def test_append_tier_with_interval_tiers(self):
        intervalTier = textgrid.IntervalTier(
            "words",
            [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")],
            minT=0,
            maxT=5.0,
        )
        intervalTier2 = textgrid.IntervalTier(
            "new_words",
            [Interval(1, 2.5, "hi"), Interval(4.1, 4.8, "planet")],
            minT=0,
            maxT=7,
        )
        sut = intervalTier.appendTier(intervalTier2)
        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(12, sut.maxTimestamp)
        self.assertEqual(
            [
                Interval(1, 2, "hello"),
                Interval(3.5, 4.0, "world"),
                Interval(6, 7.5, "hi"),
                Interval(9.1, 9.8, "planet"),
            ],
            sut._entries,
        )
        self.assertEqual(INTERVAL_TIER, sut.tierType)

    def test_find_with_interval_tiers(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
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

    def test_interval_tier_creation_with_no_times(self):
        with self.assertRaises(errors.TimelessTextgridTierException) as cm:
            textgrid.IntervalTier("phones", [], None, None)

        self.assertEqual(
            "All textgrid tiers much have a min and max duration", str(cm.exception)
        )

    @testing_utils.supressStdout
    def test_interval_tier_creation_with_invalid_entries(self):
        with self.assertRaises(errors.TextgridStateError) as _:
            textgrid.IntervalTier(
                "phones",
                [Interval(1.0, 0.0, "")],
                0.0,
                100,
            )

    def test_get_values_in_intervals(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        dataList = [
            (0.9, 100, 55),
            (1.3, 34, 92),
            (1.5, 32, 15),
            (2.6, 21, 34),
            (3.5, 31, 2),
            (3.8, 99, 44),
        ]
        self.assertEqual(
            [
                (Interval(1.0, 2.0, "hello"), [(1.3, 34, 92), (1.5, 32, 15)]),
                (Interval(2.5, 3.0, "the"), [(2.6, 21, 34)]),
                (Interval(3.5, 4.0, "world"), [(3.5, 31, 2), (3.8, 99, 44)]),
            ],
            sut.getValuesInIntervals(dataList),
        )

        dataList2 = [(0.9, 100), (1.3, 34), (1.5, 32), (4.8, 21)]
        self.assertEqual(
            [
                (Interval(1.0, 2.0, "hello"), [(1.3, 34), (1.5, 32)]),
                (Interval(2.5, 3.0, "the"), []),
                (Interval(3.5, 4.0, "world"), []),
            ],
            sut.getValuesInIntervals(dataList2),
        )

    def test_get_non_entries_when_final_interval_is_less_than_textgrid_max(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=5,
        )

        self.assertEqual(
            [Interval(0, 1, ""), Interval(3.0, 3.5, ""), Interval(4.0, 5.0, "")],
            sut.getNonEntries(),
        )

    def test_get_non_entries_when_final_interval_is_at_textgrid_max(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            maxT=4,
        )

        self.assertEqual(
            [Interval(0, 1, ""), Interval(3.0, 3.5, "")],
            sut.getNonEntries(),
        )

    def test_crop_raises_error_if_mode_invalid(self):
        sut = textgrid.Textgrid()

        with self.assertRaises(errors.WrongOption) as cm:
            sut.crop(1, 2, "cat", True)

        self.assertEqual(
            (
                "For argument 'mode' was given the value 'cat'. "
                "However, expected one of [strict, lax, truncated]"
            ),
            str(cm.exception),
        )

    def test_crop_raises_error_if_crop_start_time_occurs_after_crop_end_time(self):
        sut = makeIntervalTier()

        with self.assertRaises(errors.ArgumentError) as cm:
            sut.crop(2.1, 1.1, "lax", True)

        self.assertEqual(
            "Crop error: start time (2.1) must occur before end time (1.1)",
            str(cm.exception),
        )

    def test_crop_when_crop_area_is_empty_and_user_rebases_to_zero(self):
        originalIntervalTier = makeIntervalTier(intervals=[], minT=0, maxT=5)
        sut = originalIntervalTier.crop(
            2.0, 3.3, mode=constants.CropCollision.TRUNCATED, rebaseToZero=True
        )

        self.assertEqual(makeIntervalTier(intervals=[], minT=0, maxT=1.3), sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_truncate_and_rebase_true(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(
            2.0, 3.3, constants.CropCollision.TRUNCATED, True
        )
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0.0, 0.5, "hello"), Interval(1.0, 1.3, "world")],
            minT=0,
            maxT=1.3,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_truncate_and_rebase_false(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(
            2.0, 3.3, constants.CropCollision.TRUNCATED, False
        )
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(2.0, 2.5, "hello"), Interval(3.0, 3.3, "world")],
            minT=2.0,
            maxT=3.3,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_truncates_an_interval_if_the_crop_region_is_inside_the_interval(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(
            1.5, 2.0, constants.CropCollision.TRUNCATED, False
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1.5, 2.0, "hello")],
            minT=1.5,
            maxT=2.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_keeps_overlapping_intervals_if_mode_is_lax_and_rebase_true(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(2.0, 3.3, constants.CropCollision.LAX, True)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0.0, 1.5, "hello"), Interval(2.0, 2.5, "world")],
            minT=0,
            maxT=2.5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_keeps_overlapping_intervals_if_mode_is_lax_and_rebase_false(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(2.0, 3.3, constants.CropCollision.LAX, False)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1.0, 2.5, "hello"), Interval(3.0, 3.5, "world")],
            minT=1.0,
            maxT=3.5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_keeps_an_interval_that_is_wholly_in_crop_region_if_mode_is_lax(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(1.5, 2.0, constants.CropCollision.LAX, False)

        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2.5, "hello")],
            minT=1,
            maxT=2.5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_drops_overlapping_intervals_if_mode_is_strict_and_rebase_true(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(2.7, 2.9, "fun"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(2.0, 3.3, constants.CropCollision.STRICT, True)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0.7, 0.9, "fun")],
            minT=0,
            maxT=1.3,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_crop_drops_overlapping_intervals_if_mode_is_strict_and_rebase_false(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.7, "cats"),
                Interval(1, 2.5, "hello"),
                Interval(2.7, 2.9, "fun"),
                Interval(3.0, 3.5, "world"),
                Interval(3.5, 4.0, "travel"),
            ]
        )

        sut = originalIntervalTier.crop(2.0, 3.3, constants.CropCollision.STRICT, False)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(2.7, 2.9, "fun")], minT=2.0, maxT=3.3
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_dejitter_when_reference_tier_is_interval_tier(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(0, 0.9, "start will be modified"),
                Interval(1, 2.1, "stop will be modified"),
                Interval(2.2, 2.5, "will not be modified"),
                Interval(2.5, 3.56, "will also not be modified"),
            ]
        )
        refInterval = makeIntervalTier(
            intervals=[Interval(1, 2.0, "foo"), Interval(2.65, 3.45, "bar")]
        )
        self.assertSequenceEqual(
            [
                Interval(0, 1, "start will be modified"),
                Interval(1, 2.0, "stop will be modified"),
                Interval(2.2, 2.5, "will not be modified"),
                Interval(2.5, 3.56, "will also not be modified"),
            ],
            sut.dejitter(refInterval, 0.1)._entries,
        )

    def test_dejitter_when_reference_tier_is_point_tier(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(0, 0.9, "start will be modified"),
                Interval(1, 2.1, "stop will be modified"),
                Interval(2.2, 2.5, "will not be modified"),
                Interval(2.5, 3.56, "will also not be modified"),
            ]
        )
        refInterval = makePointTier(
            points=[
                Point(1, "foo"),
                Point(2.0, "bar"),
                Point(2.65, "bizz"),
                Point(3.45, "whomp"),
            ]
        )
        self.assertSequenceEqual(
            [
                Interval(0, 1, "start will be modified"),
                Interval(1, 2.0, "stop will be modified"),
                Interval(2.2, 2.5, "will not be modified"),
                Interval(2.5, 3.56, "will also not be modified"),
            ],
            sut.dejitter(refInterval, 0.1)._entries,
        )

    def test_delete_entry(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 4.0, "world"),
            ]
        )
        sut.deleteEntry(Interval(2.5, 3.0, "the"))
        expectedentries = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(3.2, 4.0, "world"),
            ]
        )
        self.assertEqual(sut, expectedentries)

    def test_delete_entry_throws_value_error_if_entry_does_not_exist(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 4.0, "world"),
            ]
        )

        with self.assertRaises(ValueError) as _:
            sut.deleteEntry(Interval(100, 200, "cats"))

    def test_differences(self):
        mainTier = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 4.0, "world"),
            ]
        )
        diffTier = makeIntervalTier(
            intervals=[
                Interval(0.2, 0.6, "cup"),
                Interval(1, 2.0, "think"),
                Interval(3.5, 4.2, "time"),
                Interval(5.2, 5.6, "sunlight"),
            ]
        )
        sut = mainTier.difference(diffTier)

        expectedIntervalTier = makeIntervalTier(
            intervals=[
                Interval(2, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 3.5, "world"),
            ]
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_raises_error_when_reporting_mode_is_invalid(self):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        with self.assertRaises(errors.WrongOption) as _:
            sut.editTimestamps(
                2.0,
                "cats",
            )

    def test_edit_timestamps_raises_error_when_edit_exceeds_max_time_and_reporting_mode_is_error(
        self,
    ):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                2.0,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamps_raises_error_when_edit_exceeds_min_time_and_reporting_mode_is_error(
        self,
    ):
        sut = makeIntervalTier(
            intervals=[Interval(2, 2.5, "hello"), Interval(3, 4, "world")], minT=1.0
        )

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                -2.0,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamps_when_edit_amount_is_positive_and_reporting_mode_is_silence(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")],
            minT=0.0,
            maxT=5.0,
        )

        sut = initialIntervalTier.editTimestamps(
            2.0, constants.ErrorReportingMode.SILENCE
        )
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(3, 4, "hello"), Interval(5, 6, "world")],
            minT=0.0,
            maxT=6.0,  # Bumped by the largest timestamp, not by the edit amount
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_when_edit_amount_is_negative_and_reporting_mode_is_silence(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")],
            minT=0.5,
            maxT=5.0,
        )

        sut = initialIntervalTier.editTimestamps(
            -1.0, constants.ErrorReportingMode.SILENCE
        )
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0, 1, "hello"), Interval(2, 3, "world")],
            minT=0.0,  # Modified by the smallest timestamp, not by the edit amount
            maxT=5.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_are_dropped_if_they_go_below_zero_even_with_reporting_mode_as_silence(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")]
        )

        sut = initialIntervalTier.editTimestamps(
            -2.0, constants.ErrorReportingMode.SILENCE
        )
        expectedIntervalTier = makeIntervalTier(intervals=[Interval(1, 2, "world")])
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_are_trimmed_if_they_partially_go_below_zero_and_mode_is_silence(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")]
        )

        sut = initialIntervalTier.editTimestamps(
            -1.5, constants.ErrorReportingMode.SILENCE
        )
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0, 0.5, "hello"), Interval(1.5, 2.5, "world")]
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_raises_error_if_collision_mode_is_invalid(self):
        sut = makeIntervalTier()

        with self.assertRaises(errors.WrongOption) as _:
            sut.eraseRegion(1, 2, "bird")

    def test_erase_region_does_nothing_if_there_is_no_collision_and_shrink_is_false(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        sut = originalIntervalTier.eraseRegion(
            2, 3, constants.EraseCollision.ERROR, doShrink=False
        )

        self.assertEqual(originalIntervalTier, sut)

    def test_erase_region_will_shrink_a_tier_if_shrink_is_true(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        sut = originalIntervalTier.eraseRegion(
            2, 3, constants.EraseCollision.ERROR, doShrink=True
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(2, 3, "world")], maxT=4.0
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_raises_error_if_mode_is_error(self):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )
        with self.assertRaises(errors.CollisionError) as _:
            sut.eraseRegion(
                1.5,
                3.5,
                constants.EraseCollision.ERROR,
            )

    def test_erase_region_with_truncate_mode_and_interval_covers_erase_region_and_shrink_is_true(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.5, "hello"),
                Interval(1.2, 3.8, "big"),
                Interval(4.5, 4.8, "world"),
            ],
            maxT=5.0,
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.TRUNCATE, doShrink=True
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.5, "hello"),
                Interval(1.2, 1.8, "big"),
                Interval(2.5, 2.8, "world"),
            ],
            maxT=3.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_with_truncate_mode_and_interval_covers_erase_region_and_shrink_is_false(
        self,
    ):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.5, "hello"),
                Interval(1.2, 3.8, "big"),
                Interval(4.5, 4.8, "world"),
            ]
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.TRUNCATE, doShrink=False
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.5, "hello"),
                Interval(1.2, 1.5, "big"),
                Interval(3.5, 3.8, "big"),
                Interval(4.5, 4.8, "world"),
            ]
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_with_truncate_mode_and_shrink_is_true(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.TRUNCATE, doShrink=True
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 1.5, "hello"), Interval(1.5, 2.0, "world")], maxT=3.0
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_with_truncate_mode_and_shrink_is_false(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.TRUNCATE, doShrink=False
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 1.5, "hello"), Interval(3.5, 4.0, "world")], maxT=5.0
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_with_categorical_mode_and_shrink_is_true(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "the"),
                Interval(1, 2, "hello"),
                Interval(3, 4, "world"),
                Interval(4.2, 4.5, "time"),
            ],
            maxT=5.0,
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.CATEGORICAL, doShrink=True
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "the"),
                Interval(2.2, 2.5, "time"),
            ],
            maxT=3.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_erase_region_with_categorical_mode_and_shrink_is_false(self):
        originalIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "the"),
                Interval(1, 2, "hello"),
                Interval(3, 4, "world"),
                Interval(4.2, 4.5, "time"),
            ],
            maxT=5.0,
        )

        sut = originalIntervalTier.eraseRegion(
            1.5, 3.5, constants.EraseCollision.CATEGORICAL, doShrink=False
        )

        expectedIntervalTier = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "the"),
                Interval(4.2, 4.5, "time"),
            ],
            maxT=5.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_insert_entry_raises_error_if_collision_mode_is_invalid(self):
        sut = makeIntervalTier()
        with self.assertRaises(errors.WrongOption) as _:
            sut.insertEntry(
                Interval(0, 1, "hello"),
                "bird",
                "silence",
            )

    def test_insert_entry_raises_error_if_collision_reporting_mode_is_invalid(self):
        sut = makeIntervalTier()
        with self.assertRaises(errors.WrongOption) as _:
            sut.insertEntry(
                Interval(0, 1, "hello"),
                "error",
                "bird",
            )

    def test_insert_entry_accepts_a_list(self):
        sut = makeIntervalTier(intervals=[])
        sut.insertEntry([1, 2, "hello"])

        self.assertEqual([Interval(1, 2, "hello")], sut._entries)

    def test_insert_entry_accepts_an_interval(self):
        sut = makeIntervalTier(intervals=[])
        sut.insertEntry(Interval(1, 2, "hello"))

        self.assertEqual([Interval(1, 2, "hello")], sut._entries)

    def test_insert_has_no_collision_when_boundaries_are_shared(self):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3.5, 4, "world")]
        )
        sut.insertEntry(
            [2, 3.5, "the"], collisionMode=constants.IntervalCollision.ERROR
        )

        expectedentries = [
            Interval(1, 2, "hello"),
            Interval(2, 3.5, "the"),
            Interval(3.5, 4, "world"),
        ]
        self.assertEqual(expectedentries, sut._entries)

    def test_insert_will_replace_overlapping_intervals_when_mode_is_replace(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "see"),
                Interval(1, 2, "hello"),
                Interval(3.5, 4, "world"),
                Interval(4.0, 5.0, "time"),
            ]
        )
        sut.insertEntry(
            [1.9, 3.6, "the"],
            collisionMode=constants.IntervalCollision.REPLACE,
            collisionReportingMode=constants.ErrorReportingMode.SILENCE,
        )

        expectedentries = [
            Interval(0.3, 0.8, "see"),
            Interval(1.9, 3.6, "the"),
            Interval(4.0, 5.0, "time"),
        ]
        self.assertEqual(expectedentries, sut._entries)

    def test_insert_will_merge_overlapping_intervals_when_mode_is_merge(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(0.3, 0.8, "see"),
                Interval(1, 2, "hello"),
                Interval(3.5, 4, "world"),
                Interval(4.0, 5.0, "time"),
            ]
        )
        sut.insertEntry(
            [1.9, 3.6, "the"],
            collisionMode=constants.IntervalCollision.MERGE,
            collisionReportingMode=constants.ErrorReportingMode.SILENCE,
        )

        expectedentries = [
            Interval(0.3, 0.8, "see"),
            Interval(1, 4, "hello-the-world"),
            Interval(4.0, 5.0, "time"),
        ]
        self.assertEqual(expectedentries, sut._entries)

    def test_insert_throws_error_with_overlapping_intervals_when_mode_is_error(
        self,
    ):
        sut = makeIntervalTier("words", intervals=[Interval(1, 2, "hello")])

        with self.assertRaises(errors.CollisionError) as cm:
            sut.insertEntry([1.5, 3, "world"])

        expectedErrMsg = (
            "Attempted to insert interval (1.5, 3, 'world') into tier words "
            "of textgrid but overlapping entries [(1.0, 2.0, 'hello')] already exist"
        )
        self.assertEqual(expectedErrMsg, str(cm.exception))

    def test_insert_space_raises_error_if_collision_mode_is_invalid(self):
        sut = makeIntervalTier()

        with self.assertRaises(errors.WrongOption) as _:
            sut.insertSpace(2.5, 1, "bird")

    def test_insert_space_inserts_a_space_into_the_textgrid(self):
        intervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=4,
        )

        sut = intervalTier.insertSpace(2.5, 1, "error")
        expectedIntervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(3.5, 4.0, "the"),
                Interval(4.5, 5.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_insert_space_stretches_intervals_on_collision_when_collision_code_is_stretch(
        self,
    ):
        intervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=4,
        )

        sut = intervalTier.insertSpace(2.6, 1, constants.WhitespaceCollision.STRETCH)
        expectedIntervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 4.0, "the"),
                Interval(4.5, 5.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_insert_space_splits_intervals_on_collision_when_collision_code_is_split(
        self,
    ):
        intervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=4,
        )

        sut = intervalTier.insertSpace(2.6, 1, constants.WhitespaceCollision.SPLIT)
        expectedIntervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 2.6, "the"),
                Interval(3.6, 4.0, "the"),
                Interval(4.5, 5.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_insert_space_leaves_intervals_alone_on_collision_when_collision_code_is_no_change(
        self,
    ):
        intervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=4,
        )

        sut = intervalTier.insertSpace(2.6, 1, constants.WhitespaceCollision.NO_CHANGE)
        expectedIntervalTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(4.5, 5.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_insert_space_raises_error_on_collision_when_collision_code_is_error(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ]
        )

        with self.assertRaises(errors.CollisionError) as _:
            sut.insertSpace(
                2.6,
                1,
                constants.WhitespaceCollision.ERROR,
            )

    def test_morph_when_shrinking_intervals(self):
        sourceTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),  # 1.5 seconds long
                Interval(2.5, 3.0, "the"),  # 0.5 seconds long
                Interval(3.5, 4.0, "world"),  # 0.5 seconds long
            ],
            minT=0,
            maxT=5,
        )

        targetTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(10.5, 11.5, "I"),  # 1.0 seconds long
                Interval(20.3, 20.5, "see"),  # 0.2 seconds long
                Interval(43.1, 43.4, "birds"),  # 0.3 seconds long
            ],
            minT=0,
            maxT=100,
        )

        sut = sourceTier.morph(targetTier)
        expectedIntervals = [
            Interval(1.0, 2.0, "hello"),
            Interval(2.0, 2.2, "the"),
            Interval(2.7, 3.0, "world"),
        ]

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entries)
        self.assertEqual(0, sut.minTimestamp)
        # 4.0 = 5 + (1.0 + 0.2 + 0.3) - (1.5 + 0.5 + 0.5)
        self.assertAlmostEqual(4.0, sut.maxTimestamp)

    def test_morph_when_growing_intervals(self):
        sourceTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),  # 1.5 seconds long
                Interval(2.5, 3.0, "the"),  # 0.5 seconds long
                Interval(3.5, 4.0, "world"),  # 0.5 seconds long
            ],
            minT=0,
            maxT=5,
        )

        targetTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(10.5, 13.5, "I"),  # 3 seconds long
                Interval(20.3, 25.8, "see"),  # 5.5 seconds long
                Interval(43.1, 49.7, "birds"),  # 6.6 seconds long
            ],
            minT=0,
            maxT=100,
        )

        sut = sourceTier.morph(targetTier)
        expectedIntervals = [
            Interval(1.0, 4.0, "hello"),
            Interval(4.0, 9.5, "the"),
            Interval(10.0, 16.6, "world"),
        ]

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entries)
        self.assertEqual(0, sut.minTimestamp)
        # 17.6 = 5 + (6.6 + 5.5 + 3) - (1.5 + 0.5 + 0.5)
        self.assertAlmostEqual(17.6, sut.maxTimestamp)

    def test_morph_when_tiers_have_different_numbers_of_intervals(self):
        sourceTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=5,
        )

        targetTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(10.5, 11.5, "I"),
                Interval(20.3, 20.8, "see"),
                Interval(43.1, 43.4, "birds"),
            ],
            minT=0,
            maxT=100,
        )

        with self.assertRaises(errors.SafeZipException) as _:
            sourceTier.morph(targetTier)

    def test_morph_with_filterfunc(self):
        sourceTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),  # 1.5 seconds long
                Interval(2.5, 3.0, "the"),  # 0.5 seconds long
                Interval(3.5, 4.0, "world"),  # 0.5 seconds long
            ],
            minT=0,
            maxT=5,
        )

        targetTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(10.5, 11.5, "I"),  # 1.0 seconds long
                Interval(20.3, 20.5, "see"),  # 0.2 seconds long
                Interval(43.1, 43.4, "birds"),  # 0.3 seconds long
            ],
            minT=0,
            maxT=100,
        )

        def acceptThe(label: str) -> bool:
            return label == "the"

        sut = sourceTier.morph(targetTier, filterFunc=acceptThe)

        expectedIntervals = [
            Interval(1.0, 2.5, "hello"),
            Interval(2.5, 2.7, "the"),
            Interval(3.2, 3.7, "world"),
        ]

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entries)
        self.assertEqual(0, sut.minTimestamp)
        # 4.0 = 5 + (1.0 + 0.2 + 0.3) - (1.5 + 0.5 + 0.5)
        self.assertAlmostEqual(4.7, sut.maxTimestamp)

    def test_mintimestamp_behavior(self):
        userentries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]

        # By default, the min and max timestamp values come from the entry list
        tier = textgrid.IntervalTier("test", userentries)
        self.assertEqual(0.4, tier.minTimestamp)
        self.assertEqual(1.3, tier.maxTimestamp)

        # The user can specify the min and max timestamp
        tier = textgrid.IntervalTier("test", userentries, 0.2, 2.0)
        self.assertEqual(0.2, tier.minTimestamp)
        self.assertEqual(2.0, tier.maxTimestamp)

        # When the user specified min/max timestamps are less/greater
        # than the min/max specified in the entry list, use the values
        # specified in the entry list
        tier = textgrid.IntervalTier("test", userentries, 1.0, 1.1)
        self.assertEqual(0.4, tier.minTimestamp)
        self.assertEqual(1.3, tier.maxTimestamp)

    def test_intersection_outputs_one_item_for_each_overlapping_pair(self):
        sourceTier = textgrid.IntervalTier(
            "source",
            [
                Interval(1, 2.5, "foo"),  # overlaps with 1
                Interval(2.8, 3.0, "bar"),  # overlaps with same as previous
                Interval(3, 5, "wizz"),  # overlaps with 2
            ],
            minT=0,
            maxT=5,
        )
        intersectTier = textgrid.IntervalTier(
            "target",
            [
                Interval(1, 3.0, "buzz"),
                Interval(3, 4, "cat"),
                Interval(4, 5, "dog"),
            ],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.intersection(intersectTier)
        self.assertEqual(
            [
                Interval(1.0, 2.5, "foo-buzz"),
                Interval(2.8, 3.0, "bar-buzz"),
                Interval(3, 4, "wizz-cat"),
                Interval(4, 5, "wizz-dog"),
            ],
            sut._entries,
        )

    def test_intersection_trims_non_overlapping_portions(self):
        sourceTier = textgrid.IntervalTier(
            "source",
            [
                Interval(1, 2, "foo"),  # Trim the right side
                Interval(2, 3, "bar"),  # Trim the left side
                Interval(4, 5, "cat"),  # Don't trim any part
                Interval(6, 8, "bird"),  # Trim both sides
            ],
            minT=0,
            maxT=8,
        )
        intersectTier = textgrid.IntervalTier(
            "target",
            [
                Interval(0.5, 1.5, "bang"),
                Interval(2.5, 3.5, "wizz"),
                Interval(3.5, 5.5, "dog"),
                Interval(6.5, 7.5, "fish"),
            ],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.intersection(intersectTier)
        self.assertEqual(
            [
                Interval(1, 1.5, "foo-bang"),
                Interval(2.5, 3, "bar-wizz"),
                Interval(4, 5, "cat-dog"),
                Interval(6.5, 7.5, "bird-fish"),
            ],
            sut._entries,
        )

    def test_intersection_can_specify_the_demarcator(self):
        sourceTier = textgrid.IntervalTier(
            "source",
            [Interval(1, 2, "foo")],
            minT=0,
            maxT=8,
        )
        intersectTier = textgrid.IntervalTier(
            "target",
            [Interval(0.5, 1.5, "bar")],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.intersection(intersectTier, demarcator="@")
        self.assertEqual(
            [Interval(1, 1.5, "foo@bar")],
            sut._entries,
        )

    def test_intersection_meta_info_follows_the_source_tier(self):
        tierA = textgrid.IntervalTier(
            "A",
            [
                Interval(1, 2.5, "foo"),  # overlaps with 1
                Interval(2.8, 3.0, "bar"),  # overlaps with same as previous
                Interval(3, 5, "wizz"),  # overlaps with 2
            ],
            minT=0,
            maxT=5,
        )
        tierB = textgrid.IntervalTier(
            "B",
            [
                Interval(1, 3.0, "buzz"),
                Interval(3, 4, "cat"),
                Interval(4, 5, "dog"),
            ],
            minT=0,
            maxT=9,
        )

        tierAIntersectB = tierA.intersection(tierB)
        tierBIntersectA = tierB.intersection(tierA)

        self.assertEqual(0, tierAIntersectB.minTimestamp)
        self.assertEqual(5, tierAIntersectB.maxTimestamp)
        self.assertEqual("A-B", tierAIntersectB.name)

        self.assertEqual(0, tierBIntersectA.minTimestamp)
        self.assertEqual(9, tierBIntersectA.maxTimestamp)
        self.assertEqual("B-A", tierBIntersectA.name)

    def test_merge_labels_when_the_target_intervals_are_smaller(self):
        sourceTier = textgrid.IntervalTier(
            "words",
            [
                Interval(1, 2.5, "upon"),
                Interval(2.8, 3.0, "a"),
                Interval(3.0, 4.2, "a"),
                Interval(4.2, 4.7, "time"),
            ],
            minT=0,
            maxT=5,
        )
        tierToMerge = textgrid.IntervalTier(
            "phones",
            [
                # upon
                Interval(1, 1.2, "AH0"),
                Interval(1.2, 1.3, "P"),
                Interval(1.4, 2.0, "AA1"),
                Interval(2.0, 2.5, "N"),
                # a
                Interval(2.8, 3.0, "AH0"),
                # a
                Interval(3.0, 4.2, "EY1"),
                # time
                Interval(4.2, 4.3, "T"),
                Interval(4.3, 4.6, "AY1"),
                Interval(4.6, 4.7, "M"),
            ],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.mergeLabels(tierToMerge)
        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(5, sut.maxTimestamp)
        self.assertEqual(
            [
                Interval(1.0, 2.5, "upon(AH0,P,AA1,N)"),
                Interval(2.8, 3.0, "a(AH0)"),
                Interval(3.0, 4.2, "a(EY1)"),
                Interval(4.2, 4.7, "time(T,AY1,M)"),
            ],
            sut._entries,
        )

    def test_merge_labels_when_the_target_intervals_are_larger(self):
        sourceTier = textgrid.IntervalTier(
            "phones",
            [
                # upon
                Interval(1, 1.2, "AH0"),
                Interval(1.2, 1.3, "P"),
                Interval(1.4, 2.0, "AA1"),
                Interval(2.0, 2.5, "N"),
                # a
                Interval(2.8, 3.0, "AH0"),
                # a
                Interval(3.0, 4.2, "EY1"),
                # time
                Interval(4.2, 4.3, "T"),
                Interval(4.3, 4.6, "AY1"),
                Interval(4.6, 4.7, "M"),
            ],
            minT=0,
            maxT=9,
        )
        tierToMerge = textgrid.IntervalTier(
            "words",
            [
                Interval(1, 2.5, "upon"),
                Interval(2.8, 3.0, "a"),
                Interval(3.0, 4.2, "a"),
                Interval(4.2, 4.7, "time"),
            ],
            minT=0,
            maxT=5,
        )

        sut = sourceTier.mergeLabels(tierToMerge)
        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(9, sut.maxTimestamp)
        self.assertEqual(
            [
                # upon
                Interval(1, 1.2, "AH0(upon)"),
                Interval(1.2, 1.3, "P(upon)"),
                Interval(1.4, 2.0, "AA1(upon)"),
                Interval(2.0, 2.5, "N(upon)"),
                # a
                Interval(2.8, 3.0, "AH0(a)"),
                # a
                Interval(3.0, 4.2, "EY1(a)"),
                # time
                Interval(4.2, 4.3, "T(time)"),
                Interval(4.3, 4.6, "AY1(time)"),
                Interval(4.6, 4.7, "M(time)"),
            ],
            sut._entries,
        )

    def test_merge_labels_doesnt_trim_non_overlapping_portions(self):
        sourceTier = textgrid.IntervalTier(
            "source",
            [
                Interval(1, 2, "foo"),  # Non-overlapping right side
                Interval(2, 3, "bar"),  # Non-overlapping left side
                Interval(4, 5, "cat"),  # All overlapping
                Interval(6, 8, "bird"),  # Non-overlapping on both sides
            ],
            minT=0,
            maxT=8,
        )
        tierToMerge = textgrid.IntervalTier(
            "target",
            [
                Interval(0.5, 1.5, "bang"),
                Interval(2.5, 3.5, "wizz"),
                Interval(3.5, 5.5, "dog"),
                Interval(6.5, 7.5, "fish"),
            ],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.mergeLabels(tierToMerge)
        self.assertEqual(
            [
                Interval(1, 2, "foo(bang)"),
                Interval(2, 3, "bar(wizz)"),
                Interval(4, 5, "cat(dog)"),
                Interval(6, 8, "bird(fish)"),
            ],
            sut._entries,
        )

    def test_merge_labels_can_specify_the_demarcator(self):
        sourceTier = textgrid.IntervalTier(
            "source",
            [Interval(1, 2, "foo")],
            minT=0,
            maxT=8,
        )
        tierToMerge = textgrid.IntervalTier(
            "target",
            [Interval(0.5, 1.5, "bang"), Interval(1.5, 3.5, "wizz")],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.mergeLabels(tierToMerge, demarcator="@")
        self.assertEqual(
            [
                Interval(1, 2, "foo(bang@wizz)"),
            ],
            sut._entries,
        )

    def test_to_zero_crossings(self):
        wavFN = join(self.dataRoot, "bobby.wav")
        tgFN = join(self.dataRoot, "bobby.TextGrid")

        tg = textgrid.openTextgrid(tgFN, False)
        originalTier = tg.getTier("word")

        expectedFN = join(self.dataRoot, "bobby_boundaries_at_zero_crossings.TextGrid")
        expectedTg = textgrid.openTextgrid(expectedFN, False)
        expectedTier = expectedTg.getTier("word")

        sut = originalTier.toZeroCrossings(wavFN)
        sut.name = "auto"

        # TODO: There are small differences between praat and praatio's
        #       zero-crossing calculations.
        self.assertEqual(len(expectedTier.entries), len(sut.entries))
        for entry, sutEntry in zip(expectedTier.entries, sut.entries):
            self.assertAlmostEqual(entry.start, sutEntry.start, 4)

    def test_validate_raises_error_if_an_intervals_start_happens_after_it_stops(self):
        sut = makeIntervalTier()

        self.assertTrue(sut.validate())
        sut._entries = [Interval(2.5, 1, "It's")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))

        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_raises_error_if_an_intervals_are_not_ordered_in_time(self):
        sut = makeIntervalTier()

        self.assertTrue(sut.validate())
        sut._entries = [Interval(3.5, 4.0, "world"), Interval(1, 2.5, "hello")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))

        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_raises_error_if_intervals_exist_before_min_time(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [Interval(1, 2.5, "hello"), Interval(3.5, 4.0, "world")],
            minT=1,
            maxT=5,
        )

        self.assertTrue(sut.validate())
        sut._entries = [Interval(0.5, 4.0, "world")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        with self.assertRaises(errors.OutOfBounds) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_raises_error_if_intervals_exist_after_max_time(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [Interval(1, 2.5, "hello"), Interval(3.5, 4.0, "world")],
            minT=1,
            maxT=5,
        )

        self.assertTrue(sut.validate())
        sut._entries = [Interval(0.5, 6.0, "world")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        with self.assertRaises(errors.OutOfBounds) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def assertIntervalListsAreEqual(self, expectedIntervals, actualIntervals):
        self.assertAllAlmostEqual(
            [interval.start for interval in expectedIntervals],
            [interval.start for interval in actualIntervals],
        )

        self.assertAllAlmostEqual(
            [interval.end for interval in expectedIntervals],
            [interval.end for interval in actualIntervals],
        )

        self.assertEqual(
            [interval.label for interval in expectedIntervals],
            [interval.label for interval in actualIntervals],
        )


if __name__ == "__main__":
    unittest.main()
