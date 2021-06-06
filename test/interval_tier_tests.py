import unittest

from praatio import textgrid
from praatio.utilities.constants import Interval, INTERVAL_TIER
from praatio.utilities import errors
from praatio.utilities import constants

from test.praatio_test_case import PraatioTestCase
from test import testing_utils


def makeIntervalTier(name="words", intervals=None, minT=0, maxT=5.0):
    if intervals is None:
        intervals = [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")]
    return textgrid.IntervalTier(name, intervals, minT, maxT)


class IntervalTierTests(PraatioTestCase):
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
            sut.entryList,
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
        self.assertRaises(
            errors.TimelessTextgridTierException,
            textgrid.IntervalTier,
            "phones",
            [],
            None,
            None,
        )

    @testing_utils.supressStdout
    def test_interval_tier_creation_with_invalid_entries(self):
        self.assertRaises(
            errors.TextgridException,
            textgrid.IntervalTier,
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
                [(1.3, 34, 92), (1.5, 32, 15)],
                [(2.6, 21, 34)],
                [(3.5, 31, 2), (3.8, 99, 44)],
            ],
            sut.getValuesInIntervals(dataList),
        )

        dataList2 = [(0.9, 100), (1.3, 34), (1.5, 32), (4.8, 21)]
        self.assertEqual(
            [[(1.3, 34), (1.5, 32)], [], []],
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
        sut = makeIntervalTier()

        self.assertRaises(errors.WrongOption, sut.crop, 1, 2, "bird", False)

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
            intervals=[Interval(0.0, 0.2, "fun")],
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
            intervals=[Interval(2.7, 2.9, "fun")],
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_delete_entry(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 4.0, "world"),
            ]
        )
        sut.deleteEntry(Interval(2.5, 3.0, "the"))
        expectedEntryList = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(3.2, 4.0, "world"),
            ]
        )
        self.assertEqual(sut, expectedEntryList)

    def test_delete_entry_throws_value_error_if_entry_does_not_exist(self):
        sut = makeIntervalTier(
            intervals=[
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.2, 4.0, "world"),
            ]
        )

        self.assertRaises(ValueError, sut.deleteEntry, Interval(100, 200, "cats"))

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

    def test_edit_timestamps_raises_error_when_edit_exceeds_max_time_and_allow_overshoot_is_false(
        self,
    ):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], maxT=5.0
        )

        self.assertRaises(errors.TextgridException, sut.editTimestamps, 2.0, False)

    def test_edit_timestamps_raises_error_when_edit_exceeds_min_time_and_allow_overshoot_is_false(
        self,
    ):
        sut = makeIntervalTier(
            intervals=[Interval(2, 2.5, "hello"), Interval(3, 4, "world")], minT=1.0
        )

        self.assertRaises(errors.TextgridException, sut.editTimestamps, -2.0, False)

    def test_edit_timestamps_when_edit_amount_is_positive_and_allow_overshoot_is_true(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")],
            minT=0.0,
            maxT=5.0,
        )

        sut = initialIntervalTier.editTimestamps(2.0, True)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(3, 4, "hello"), Interval(5, 6, "world")],
            minT=0.0,
            maxT=6.0,  # Bumped by the largest timestamp, not by the edit amount
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_when_edit_amount_is_negative_and_allow_overshoot_is_true(
        self,
    ):
        initialIntervalTier = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")],
            minT=0.5,
            maxT=5.0,
        )

        sut = initialIntervalTier.editTimestamps(-1.0, True)
        expectedIntervalTier = makeIntervalTier(
            intervals=[Interval(0, 1, "hello"), Interval(2, 3, "world")],
            minT=0.0,  # Modified by the smallest timestamp, not by the edit amount
            maxT=5.0,
        )
        self.assertEqual(expectedIntervalTier, sut)

    def test_edit_timestamps_raises_error_if_times_go_below_zero_even_with_overshoot_true(
        self,
    ):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3, 4, "world")], minT=0.0
        )

        self.assertRaises(errors.TextgridException, sut.editTimestamps, -2.0, True)

    def test_erase_region_raises_error_if_collision_mode_is_invalid(self):
        sut = makeIntervalTier()
        self.assertRaises(errors.WrongOption, sut.eraseRegion, 1, 2, "bird")

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
        self.assertRaises(
            errors.TextgridException,
            sut.eraseRegion,
            1.5,
            3.5,
            constants.EraseCollision.ERROR,
        )

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
        self.assertRaises(
            errors.WrongOption,
            sut.insertEntry,
            Interval(0, 1, "hello"),
            "bird",
            "silence",
        )

    def test_insert_entry_raises_error_if_collision_reporting_mode_is_invalid(self):
        sut = makeIntervalTier()
        self.assertRaises(
            errors.WrongOption,
            sut.insertEntry,
            Interval(0, 1, "hello"),
            "error",
            "bird",
        )

    def test_insert_entry_accepts_a_list(self):
        sut = makeIntervalTier(intervals=[])
        sut.insertEntry([1, 2, "hello"])

        self.assertEqual([Interval(1, 2, "hello")], sut.entryList)

    def test_insert_has_no_collision_when_boundaries_are_shared(self):
        sut = makeIntervalTier(
            intervals=[Interval(1, 2, "hello"), Interval(3.5, 4, "world")]
        )
        sut.insertEntry(
            [2, 3.5, "the"], collisionMode=constants.IntervalCollision.ERROR
        )

        expectedEntryList = [
            Interval(1, 2, "hello"),
            Interval(2, 3.5, "the"),
            Interval(3.5, 4, "world"),
        ]
        self.assertEqual(expectedEntryList, sut.entryList)

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

        expectedEntryList = [
            Interval(0.3, 0.8, "see"),
            Interval(1.9, 3.6, "the"),
            Interval(4.0, 5.0, "time"),
        ]
        self.assertEqual(expectedEntryList, sut.entryList)

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

        expectedEntryList = [
            Interval(0.3, 0.8, "see"),
            Interval(1, 4, "hello-the-world"),
            Interval(4.0, 5.0, "time"),
        ]
        self.assertEqual(expectedEntryList, sut.entryList)

    def test_insert_throws_error_with_overlapping_intervals_when_mode_is_error(
        self,
    ):
        sut = makeIntervalTier(intervals=[Interval(1, 2, "hello")])

        self.assertRaises(
            errors.TextgridCollisionException, sut.insertEntry, [1.5, 3, "world"]
        )

    def test_insert_space_raises_error_if_collision_mode_is_invalid(self):
        sut = makeIntervalTier()
        self.assertRaises(errors.WrongOption, sut.insertSpace, 2.5, 1, "bird")

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

        self.assertRaises(
            errors.PraatioException,
            sut.insertSpace,
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

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entryList)
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

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entryList)
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

        self.assertRaises(errors.SafeZipException, sourceTier.morph, targetTier)

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

        self.assertIntervalListsAreEqual(expectedIntervals, sut.entryList)
        self.assertEqual(0, sut.minTimestamp)
        # 4.0 = 5 + (1.0 + 0.2 + 0.3) - (1.5 + 0.5 + 0.5)
        self.assertAlmostEqual(4.7, sut.maxTimestamp)

    def test_mintimestamp_behaviour(self):
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]

        # By default, the min and max timestamp values come from the entry list
        tier = textgrid.IntervalTier("test", userEntryList)
        self.assertEqual(0.4, tier.minTimestamp)
        self.assertEqual(1.3, tier.maxTimestamp)

        # The user can specify the min and max timestamp
        tier = textgrid.IntervalTier("test", userEntryList, 0.2, 2.0)
        self.assertEqual(0.2, tier.minTimestamp)
        self.assertEqual(2.0, tier.maxTimestamp)

        # When the user specified min/max timestamps are less/greater
        # than the min/max specified in the entry list, use the values
        # specified in the entry list
        tier = textgrid.IntervalTier("test", userEntryList, 1.0, 1.1)
        self.assertEqual(0.4, tier.minTimestamp)
        self.assertEqual(1.3, tier.maxTimestamp)

    def test_intersection(self):
        sourceTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.8, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=5,
        )
        intersectTier = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "It's"),
                Interval(3.0, 3.5, "my"),
                Interval(3.7, 4.2, "cat"),
                Interval(4.3, 4.7, "there"),
            ],
            minT=0,
            maxT=9,
        )

        sut = sourceTier.intersection(intersectTier)
        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(5, sut.maxTimestamp)
        self.assertEqual(
            [Interval(1.0, 2.5, "hello-It's"), Interval(3.7, 4.0, "world-cat")],
            sut.entryList,
        )

    def test_validate_raises_error_if_an_intervals_start_happens_after_it_stops(self):
        sut = makeIntervalTier()

        self.assertTrue(sut.validate())
        sut.entryList = [Interval(2.5, 1, "It's")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        self.assertRaises(
            errors.TextgridException, sut.validate, constants.ErrorReportingMode.ERROR
        )

    def test_validate_raises_error_if_an_intervals_are_not_ordered_in_time(self):
        sut = makeIntervalTier()

        self.assertTrue(sut.validate())
        sut.entryList = [Interval(3.5, 4.0, "world"), Interval(1, 2.5, "hello")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        self.assertRaises(
            errors.TextgridException, sut.validate, constants.ErrorReportingMode.ERROR
        )

    def test_validate_raises_error_if_intervals_exist_before_min_time(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [Interval(1, 2.5, "hello"), Interval(3.5, 4.0, "world")],
            minT=1,
            maxT=5,
        )

        self.assertTrue(sut.validate())
        sut.entryList = [Interval(0.5, 4.0, "world")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        self.assertRaises(
            errors.TextgridException, sut.validate, constants.ErrorReportingMode.ERROR
        )

    def test_validate_raises_error_if_intervals_exist_after_max_time(self):
        sut = textgrid.IntervalTier(
            "pitch_values",
            [Interval(1, 2.5, "hello"), Interval(3.5, 4.0, "world")],
            minT=1,
            maxT=5,
        )

        self.assertTrue(sut.validate())
        sut.entryList = [Interval(0.5, 6.0, "world")]
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))
        self.assertRaises(
            errors.TextgridException, sut.validate, constants.ErrorReportingMode.ERROR
        )

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
