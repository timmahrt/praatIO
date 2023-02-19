import unittest

from praatio import textgrid
from praatio.utilities.constants import Interval, Point
from praatio.utilities import constants
from praatio.utilities import errors

from tests.praatio_test_case import PraatioTestCase


def makeIntervalTier(name="words", intervals=None, minT=0, maxT=5.0):
    if intervals is None:
        intervals = [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")]
    return textgrid.IntervalTier(name, intervals, minT, maxT)


def makePointTier(name="pitch_values", points=None, minT=0, maxT=5.0):
    if points is None:
        points = [Point(1.3, "55"), Point(3.7, "99")]
    return textgrid.PointTier(name, points, minT, maxT)


class TestTextgrid(PraatioTestCase):
    def test_inequivalence_with_non_textgrids(self):
        sut = textgrid.Textgrid()
        self.assertNotEqual(sut, 55)

    def test_add_tier_raises_error_with_invalid_option(self):
        sut = textgrid.Textgrid()
        tier = makeIntervalTier()

        with self.assertRaises(errors.WrongOption) as _:
            sut.addTier(tier, reportingMode="bird")

    def test_add_tier_raises_error_if_max_timestamp_is_altered(self):
        sut = textgrid.Textgrid(maxTimestamp=5)
        tier = makeIntervalTier(maxT=10)

        with self.assertRaises(errors.TextgridStateAutoModified) as _:
            sut.addTier(tier, reportingMode="error")

    def test_add_tier_raises_error_if_min_timestamp_is_altered(self):
        sut = textgrid.Textgrid(minTimestamp=3)
        tier = makeIntervalTier(minT=1)

        with self.assertRaises(errors.TextgridStateAutoModified) as _:
            sut.addTier(tier, reportingMode="error")

    def test_add_tier_raises_error_if_autoset_max_timestamp_is_altered(self):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier("words", maxT=5)
        tier2 = makeIntervalTier("phrases", maxT=10)

        sut.addTier(tier1, reportingMode="error")
        with self.assertRaises(errors.TextgridStateAutoModified) as _:
            sut.addTier(tier2, reportingMode="error")

    def test_add_tier_raises_error_if_autoset_min_timestamp_is_altered(self):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier("words", minT=1)
        tier2 = makeIntervalTier("phrases", minT=0.5)

        sut.addTier(tier1, reportingMode="error")
        with self.assertRaises(errors.TextgridStateAutoModified) as _:
            sut.addTier(tier2, reportingMode="error")

    def test_add_tier_raises_error_if_tier_name_already_exists_in_textgrid(self):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier("words")
        tier2 = makeIntervalTier("words")

        sut.addTier(tier1, reportingMode="error")
        with self.assertRaises(errors.TierNameExistsError) as _:
            sut.addTier(tier2)

    def test_add_tier_can_add_a_tier_to_a_tg(self):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier("words")
        tier2 = makeIntervalTier("phrases")
        tier3 = makePointTier("max pitch")

        sut.addTier(tier1, reportingMode="error")
        sut.addTier(tier2, reportingMode="error")
        sut.addTier(tier3, reportingMode="error")

        self.assertSequenceEqual(["words", "phrases", "max pitch"], sut.tierNames)
        self.assertEqual(tier1, sut.getTier("words"))
        self.assertEqual(tier2, sut.getTier("phrases"))
        self.assertEqual(tier3, sut.getTier("max pitch"))

    def test_add_tier_can_add_a_tier_to_a_tg_at_specific_indices(self):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier("words")
        tier2 = makeIntervalTier("phrases")
        tier3 = makePointTier("max pitch")

        sut.addTier(tier1, reportingMode="error")
        sut.addTier(tier2, reportingMode="error")
        sut.addTier(tier3, tierIndex=1, reportingMode="error")

        # tier3 was inserted last but with index 1, so it will appear second
        self.assertSequenceEqual(["words", "max pitch", "phrases"], sut.tierNames)
        self.assertEqual(tier1, sut.getTier("words"))
        self.assertEqual(tier3, sut.getTier("max pitch"))
        self.assertEqual(tier2, sut.getTier("phrases"))

    def test_manually_replacing_a_tier_doesnt_unintentionally_modifying_order(
        self,
    ):
        # Users are not supposed to directly modify tierDict directly, but
        # it might be difficult to actually enforce this
        expectedTierNameList = ["words", "phrases"]

        tier1 = makeIntervalTier("words")
        tier2 = makeIntervalTier("phrases")

        tier3 = makeIntervalTier("words")
        tier3.insertEntry((0, 1.0, "hello"))

        self.assertNotEqual(tier1, tier3)

        sut = textgrid.Textgrid()
        sut.addTier(tier1)
        sut.addTier(tier2)

        self.assertSequenceEqual(expectedTierNameList, sut.tierNames)

        sut._tierDict["words"] = tier3
        self.assertSequenceEqual(expectedTierNameList, sut.tierNames)
        self.assertEqual(tier3, sut.getTier("words"))

    def test_manually_updating_tier_dict_also_updates_tier_name_list(self):
        # Users are not supposed to directly modify tierDict directly, but
        # it might be difficult to actually enforce this
        tier1 = makeIntervalTier("words")
        tier2 = makeIntervalTier("phrases")

        sut = textgrid.Textgrid()
        sut._tierDict["words"] = tier1
        self.assertSequenceEqual(["words"], sut.tierNames)

        sut.addTier(tier2)
        sut._tierDict["phrases"] = tier1
        self.assertSequenceEqual(["words", "phrases"], sut.tierNames)

    def test_append_textgrid_with_matching_names_only(self):
        tg1 = textgrid.Textgrid()
        tg2 = textgrid.Textgrid()
        tier1 = makeIntervalTier("words", [[1.1, 2.3, "hello"], [3.4, 4.1, "world"]])
        tier2 = makeIntervalTier("words", [[2.4, 3.0, "goodnight"], [3.4, 4.1, "moon"]])
        tier3 = makePointTier("max pitch", [[1.8, "135"], [3.7, "152"]])
        tier4 = makePointTier("max pitch", [[2.7, "98"], [3.8, "143"]])
        tier5 = makeIntervalTier("phrases", [[0.9, 1.3, "the"], [2.0, 2.4, "house"]])
        tier6 = makeIntervalTier("cats", [[1.9, 2.3, "birds"], [3.2, 4.1, "fly"]])
        tier7 = makePointTier("min pitch", [[1.4, "61"], [4.1, "73"]])
        tier8 = makePointTier("dogs", [[2.7, "collie"], [3.8, "golden retriever"]])

        for tier in [tier1, tier3, tier5, tier7]:
            tg1.addTier(tier)
        for tier in [tier2, tier4, tier6, tier8]:
            tg2.addTier(tier)

        sut = tg1.appendTextgrid(tg2, onlyMatchingNames=True)

        expectedTier1 = makeIntervalTier(
            "words",
            [
                [1.1, 2.3, "hello"],
                [3.4, 4.1, "world"],
                [7.4, 8.0, "goodnight"],
                [8.4, 9.1, "moon"],
            ],
            0,
            10,
        )
        expectedTier2 = makePointTier(
            "max pitch", [[1.8, "135"], [3.7, "152"], [7.7, "98"], [8.8, "143"]], 0, 10
        )

        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(10, sut.maxTimestamp)
        self.assertSequenceEqual(["words", "max pitch"], sut.tierNames)
        self.assertEqual(expectedTier1, sut.getTier("words"))
        self.assertEqual(expectedTier2, sut.getTier("max pitch"))

    def test_append_textgrid_without_matching_names_only(self):
        tg1 = textgrid.Textgrid()
        tg2 = textgrid.Textgrid()
        tier1 = makeIntervalTier("words", [[1.1, 2.3, "hello"], [3.4, 4.1, "world"]])
        tier2 = makeIntervalTier("words", [[2.4, 3.0, "goodnight"], [3.4, 4.1, "moon"]])
        tier3 = makePointTier("max pitch", [[1.8, "135"], [3.7, "152"]])
        tier4 = makePointTier("max pitch", [[2.7, "98"], [3.8, "143"]])
        tier5 = makeIntervalTier("phrases", [[0.9, 1.3, "the"], [2.0, 2.4, "house"]])
        tier6 = makeIntervalTier("cats", [[1.9, 2.3, "birds"], [3.2, 4.1, "fly"]])
        tier7 = makePointTier("min pitch", [[1.4, "61"], [4.1, "73"]])
        tier8 = makePointTier("dogs", [[2.7, "collie"], [3.8, "golden retriever"]])

        for tier in [tier1, tier3, tier5, tier7]:
            tg1.addTier(tier)
        for tier in [tier2, tier4, tier6, tier8]:
            tg2.addTier(tier)

        sut = tg1.appendTextgrid(tg2, onlyMatchingNames=False)

        expectedTier1 = makeIntervalTier(
            "words",
            [
                [1.1, 2.3, "hello"],
                [3.4, 4.1, "world"],
                [7.4, 8.0, "goodnight"],
                [8.4, 9.1, "moon"],
            ],
            0,
            10,
        )
        expectedTier2 = makePointTier(
            "max pitch", [[1.8, "135"], [3.7, "152"], [7.7, "98"], [8.8, "143"]], 0, 10
        )
        expectedTier3 = makeIntervalTier(
            "phrases", [[0.9, 1.3, "the"], [2.0, 2.4, "house"]]
        )
        expectedTier4 = makePointTier("min pitch", [[1.4, "61"], [4.1, "73"]])
        expectedTier5 = makeIntervalTier(
            "cats", [[6.9, 7.3, "birds"], [8.2, 9.1, "fly"]], 0, 10
        )
        expectedTier6 = makePointTier(
            "dogs", [[7.7, "collie"], [8.8, "golden retriever"]], 0, 10
        )

        self.assertEqual(0, sut.minTimestamp)
        self.assertEqual(10, sut.maxTimestamp)
        self.assertSequenceEqual(
            ["words", "max pitch", "phrases", "min pitch", "cats", "dogs"],
            sut.tierNames,
        )
        self.assertEqual(expectedTier1, sut.getTier("words"))
        self.assertEqual(expectedTier2, sut.getTier("max pitch"))
        self.assertEqual(expectedTier3, sut.getTier("phrases"))
        self.assertEqual(expectedTier4, sut.getTier("min pitch"))
        self.assertEqual(expectedTier5, sut.getTier("cats"))
        self.assertEqual(expectedTier6, sut.getTier("dogs"))

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
        sut = textgrid.Textgrid()

        with self.assertRaises(errors.ArgumentError) as cm:
            sut.crop(2.1, 1.1, "lax", True)

        self.assertEqual(
            "Crop error: start time (2.1) must occur before end time (1.1)",
            str(cm.exception),
        )

    def test_crop_truncates_overlapping_intervals_if_mode_is_truncate_and_rebase_true(
        self,
    ):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 3.7, constants.CropCollision.TRUNCATED, True)
        expectedTextgrid = textgrid.Textgrid(0, 1.2)
        for tier in [
            makeIntervalTier("phrases", [[0.5, 1.2, "world"]], maxT=1.2),
            makePointTier("cats", [[1.1, "soda"]], maxT=1.2),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_truncate_and_rebase_false(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(0, 6)
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 3.7, constants.CropCollision.TRUNCATED, False)
        expectedTextgrid = textgrid.Textgrid(2.5, 3.7)
        for tier in [
            makeIntervalTier("phrases", [[3, 3.7, "world"]], 2.5, 3.7),
            makePointTier("cats", [[3.6, "soda"]], 2.5, 3.7),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_strict_and_rebase_true(
        self,
    ):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 5.8, constants.CropCollision.STRICT, True)
        expectedTextgrid = textgrid.Textgrid(0, 3.3)
        for tier in [
            makeIntervalTier("phrases", [[0.5, 1.5, "world"]], maxT=3.3),
            makePointTier("cats", [[1.1, "soda"]], maxT=3.3),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_strict_and_rebase_false(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(0, 6)
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 5.8, constants.CropCollision.STRICT, False)
        expectedTextgrid = textgrid.Textgrid(2.5, 5.8)
        for tier in [
            makeIntervalTier("phrases", [[3, 4, "world"]], 2.5, 5.8),
            makePointTier("cats", [[3.6, "soda"]], 2.5, 5.8),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_lax_and_rebase_true(
        self,
    ):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 3.7, constants.CropCollision.LAX, True)
        expectedTextgrid = textgrid.Textgrid(0, 1.5)
        for tier in [
            makeIntervalTier("phrases", [[0.5, 1.5, "world"]], maxT=1.5),
            makePointTier("cats", [[1.1, "soda"]], maxT=1.2),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_crop_truncates_overlapping_intervals_if_mode_is_lax_and_rebase_false(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(0, 6)
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.crop(2.5, 3.7, constants.CropCollision.LAX, False)
        expectedTextgrid = textgrid.Textgrid(2.5, 4)
        for tier in [
            makeIntervalTier("phrases", [[3, 4, "world"]], 2.5, 4),
            makePointTier("cats", [[3.6, "soda"]], 2.5, 3.7),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_erase_region_removes_entries(self):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.eraseRegion(2.5, 4.3, False)
        expectedTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [5.5, 6, "goodnight"]]),
            makePointTier("cats", [[1, "ice cream"], [4.6, "pizza"]]),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_erase_region_truncates_partially_overlapping_intervals(self):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.eraseRegion(3.5, 4.5, False)
        expectedTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 3.5, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [4.6, "pizza"]]),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_erase_region_removes_entries_shrinks_the_textgrid_if_do_shrink_is_true(
        self,
    ):
        originalTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases",
                [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]],
                maxT=5,
            ),
            makePointTier(
                "cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]], maxT=5
            ),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.eraseRegion(2.5, 4, True)
        expectedTextgrid = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [4, 4.5, "goodnight"]], maxT=4.5
            ),
            makePointTier("cats", [[1, "ice cream"], [3.1, "pizza"]], maxT=3.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_erase_region_raises_error_if_deletion_start_time_is_after_end_time(self):
        sut = textgrid.Textgrid()
        for tier in [
            makeIntervalTier(
                "phrases", [[1, 2, "hello"], [3, 4, "world"], [5.5, 6, "goodnight"]]
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "soda"], [4.6, "pizza"]]),
        ]:
            sut.addTier(tier)

        with self.assertRaises(errors.ArgumentError) as _:
            sut.eraseRegion(2, 1, False)

    def test_edit_timestamps_throws_error_if_reporting_mode_is_invalid(self):
        sut = textgrid.Textgrid(0, 7)

        with self.assertRaises(errors.WrongOption) as _:
            sut.editTimestamps(3.0, "cats")

    def test_edit_timestamps_can_move_times_forward(self):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=6),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=6),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.editTimestamps(1.1, constants.ErrorReportingMode.ERROR)
        expectedTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier(
                "phrases", [[2.1, 3.1, "hello"], [4.1, 5.1, "world"]], maxT=6
            ),
            makePointTier("cats", [[2.1, "ice cream"], [4.7, "pizza"]], maxT=6),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_edit_timestamps_can_move_times_past_max_timestamp_if_reporting_mode_is_silence(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(0, 5)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=4),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=4),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.editTimestamps(1.1, constants.ErrorReportingMode.SILENCE)
        expectedTextgrid = textgrid.Textgrid(0, 5.1)
        for tier in [
            makeIntervalTier(
                "phrases", [[2.1, 3.1, "hello"], [4.1, 5.1, "world"]], maxT=5.1
            ),
            makePointTier("cats", [[2.1, "ice cream"], [4.7, "pizza"]], maxT=4.7),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_edit_timestamps_throws_error_if_max_timestamp_exceeded_and_reporting_mode_is_error(
        self,
    ):
        sut = textgrid.Textgrid(0, 5)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=4),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=4),
        ]:
            sut.addTier(tier)

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                3.0,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamps_can_move_times_backwards(self):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]]),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.editTimestamps(-0.5, constants.ErrorReportingMode.ERROR)
        expectedTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[0.5, 1.5, "hello"], [2.5, 3.5, "world"]]),
            makePointTier("cats", [[0.5, "ice cream"], [3.1, "pizza"]]),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_edit_timestamps_can_move_times_past_mintimestamp_if_reporting_mode_is_silence(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(1, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], minT=1),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], minT=1),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.editTimestamps(
            -0.5, constants.ErrorReportingMode.SILENCE
        )
        expectedTextgrid = textgrid.Textgrid(0.5, 7)
        for tier in [
            makeIntervalTier(
                "phrases", [[0.5, 1.5, "hello"], [2.5, 3.5, "world"]], minT=0.5
            ),
            makePointTier("cats", [[0.5, "ice cream"], [3.1, "pizza"]], minT=0.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_edit_timestamps_throws_error_if_min_timestamp_exceeded_and_reporting_mode_is_error(
        self,
    ):
        sut = textgrid.Textgrid(0.6, 5)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], minT=0.7),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], minT=0.6),
        ]:
            sut.addTier(tier)

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                -0.5,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamps_throws_error_if_times_become_negative_and_reporting_mode_is_error(
        self,
    ):
        sut = textgrid.Textgrid(0, 5)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], minT=0),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], minT=0),
        ]:
            sut.addTier(tier)

        with self.assertRaises(errors.OutOfBounds) as _:
            sut.editTimestamps(
                -1.5,
                constants.ErrorReportingMode.ERROR,
            )

    def test_edit_timestamps_truncates_entries_with_negative_times_when_reporting_mode_is_silence(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(1, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], minT=1.0),
            makePointTier(
                "cats", [[1, "ice cream"], [1.6, "soda"], [3.6, "pizza"]], minT=1.0
            ),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.editTimestamps(
            -1.5, constants.ErrorReportingMode.SILENCE
        )
        expectedTextgrid = textgrid.Textgrid(0.0, 7)
        for tier in [
            makeIntervalTier(
                "phrases", [[0, 0.5, "hello"], [1.5, 2.5, "world"]], minT=0
            ),
            makePointTier("cats", [[0.1, "soda"], [2.1, "pizza"]], minT=0.1),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_insert_space(self):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=5),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.insertSpace(0, 0.5)
        expectedTextgrid = textgrid.Textgrid(0, 7.5)
        for tier in [
            makeIntervalTier(
                "phrases", [[1.5, 2.5, "hello"], [3.5, 4.5, "world"]], maxT=5.5
            ),
            makePointTier("cats", [[1.5, "ice cream"], [4.1, "pizza"]], maxT=5.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_insert_space_stretches_on_collision_if_mode_is_stretch(self):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=5),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.insertSpace(
            3.6, 0.5, constants.WhitespaceCollision.STRETCH
        )
        expectedTextgrid = textgrid.Textgrid(0, 7.5)
        for tier in [
            makeIntervalTier(
                "phrases",
                [[1, 2, "hello"], [3, 4.5, "world"]],
                maxT=5.5,
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_insert_space_splits_on_collision_if_mode_is_split(self):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=5),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.insertSpace(
            3.6, 0.5, constants.WhitespaceCollision.SPLIT
        )
        expectedTextgrid = textgrid.Textgrid(0, 7.5)
        for tier in [
            makeIntervalTier(
                "phrases",
                [[1, 2, "hello"], [3, 3.6, "world"], [4.1, 4.5, "world"]],
                maxT=5.5,
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_insert_space_does_not_change_entries_on_collision_if_mode_is_no_change(
        self,
    ):
        originalTextgrid = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=5),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.insertSpace(
            3.6, 0.5, constants.WhitespaceCollision.NO_CHANGE
        )
        expectedTextgrid = textgrid.Textgrid(0, 7.5)
        for tier in [
            makeIntervalTier(
                "phrases",
                [[1, 2, "hello"], [3, 4, "world"]],
                maxT=5.5,
            ),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5.5),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_insert_space_raises_error_on_collision_if_mode_is_error(self):
        sut = textgrid.Textgrid(0, 7)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [3, 4, "world"]], maxT=5),
            makePointTier("cats", [[1, "ice cream"], [3.6, "pizza"]], maxT=5),
        ]:
            sut.addTier(tier)

        with self.assertRaises(errors.CollisionError) as _:
            sut.insertSpace(
                1.5,
                2,
                constants.WhitespaceCollision.ERROR,
            )

    def test_merge_tiers_wont_include_merged_tiers_if_preserve_other_tiers_false(self):
        originalTextgrid = textgrid.Textgrid(0, 7)

        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
            makePointTier("cats", [[1, "ice cream"]]),
            makePointTier("dogs", [[5.5, "chocolate"]]),
            makePointTier("birds", [[3, "yogurt"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.mergeTiers(["phrases", "words", "cats", "birds"], False)

        expectedTextgrid = textgrid.Textgrid(0, 7)

        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"], [5, 6.7, "hey there"]]),
            makePointTier("cats", [[1, "ice cream"], [3, "yogurt"]]),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_merge_tiers_can_combine_a_subset_of_tiers(self):
        originalTextgrid = textgrid.Textgrid(0, 7)

        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
            makePointTier("cats", [[1, "ice cream"]]),
            makePointTier("dogs", [[5.5, "chocolate"]]),
            makePointTier("birds", [[3, "yogurt"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.mergeTiers(["phrases", "words", "cats", "birds"])

        expectedTextgrid = textgrid.Textgrid(0, 7)

        for tier in [
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
            makePointTier("dogs", [[5.5, "chocolate"]]),
            makeIntervalTier("phrases", [[1, 2, "hello"], [5, 6.7, "hey there"]]),
            makePointTier("cats", [[1, "ice cream"], [3, "yogurt"]]),
        ]:
            expectedTextgrid.addTier(tier)

        self.assertEqual(expectedTextgrid, sut)

    def test_merge_tiers_can_combine_all_tiers(self):
        originalTextgrid = textgrid.Textgrid(0, 10)

        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
            makePointTier("cats", [[1, "ice cream"]]),
            makePointTier("dogs", [[5.5, "chocolate"]]),
            makePointTier("birds", [[3, "yogurt"]]),
        ]:
            originalTextgrid.addTier(tier)

        sut = originalTextgrid.mergeTiers()

        expectedTextgrid = textgrid.Textgrid(0, 10)
        expectedMergedTier1 = makeIntervalTier(
            "phrases", [[1, 2, "hello"], [3, 4, "goodbye"], [5, 6.7, "hey there"]]
        )
        expectedMergedTier2 = makePointTier(
            "cats", [[1, "ice cream"], [3, "yogurt"], [5.5, "chocolate"]]
        )
        expectedTextgrid.addTier(expectedMergedTier1)
        expectedTextgrid.addTier(expectedMergedTier2)

        self.assertEqual(expectedTextgrid, sut)

    def test_new_creates_a_copy_of_itself(self):
        sut = textgrid.Textgrid(0, 12)

        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
        ]:
            sut.addTier(tier)

        sutCopy = sut.new()
        self.assertEqual(sutCopy, sut)

        tier4 = makeIntervalTier("dogs", [[9, 11, "see you soon"]])
        sutCopy.addTier(tier4)
        self.assertNotEqual(sutCopy, sut)

    def test_save_throws_error_if_output_format_is_invalid(self):
        sut = textgrid.Textgrid()

        with self.assertRaises(errors.WrongOption) as _:
            sut.save(
                "file.Textgrid",
                format="cat",
                includeBlankSpaces=True,
            )

    def test_save_throws_error_if_reporting_mode_is_invalid(self):
        sut = textgrid.Textgrid()

        with self.assertRaises(errors.WrongOption) as _:
            sut.save(
                "file.Textgrid",
                format="short_textgrid",
                includeBlankSpaces=True,
                reportingMode="cat",
            )

    def test_rename_tier_renames_a_tier(self):
        sut = textgrid.Textgrid(0, 10)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
        ]:
            sut.addTier(tier)

        sut.renameTier("words", "cats")
        expectedRenamedTier = makeIntervalTier("cats", [[5, 6.7, "hey there"]])

        self.assertEqual(expectedRenamedTier, sut.getTier("cats"))
        self.assertSequenceEqual(["phrases", "cats", "phones"], sut.tierNames)

    def test_remove_tier_removes_a_tier(self):
        sut = textgrid.Textgrid(0, 10)
        for tier in [
            makeIntervalTier("phrases", [[1, 2, "hello"]]),
            makeIntervalTier("words", [[5, 6.7, "hey there"]]),
            makeIntervalTier("phones", [[3, 4, "goodbye"]]),
        ]:
            sut.addTier(tier)

        tier2 = sut.getTier("words")
        removedTier = sut.removeTier("words")

        self.assertEqual(removedTier, tier2)
        self.assertSequenceEqual(["phrases", "phones"], sut.tierNames)

    def test_replace_tier_replaces_one_tier_with_another(self):
        sut = textgrid.Textgrid(0, 10)
        tier1 = makeIntervalTier("words", intervals=[[1, 2, "hello"]])
        tier2 = makeIntervalTier("phones", intervals=[[5, 6.7, "hey there"]])
        newTier1 = makeIntervalTier("cats", intervals=[[3, 4, "goodbye"]])

        sut.addTier(tier1)
        sut.addTier(tier2)

        self.assertSequenceEqual(["words", "phones"], sut.tierNames)

        sut.replaceTier("words", newTier1)

        self.assertSequenceEqual(["cats", "phones"], sut.tierNames)
        self.assertEqual(newTier1, sut.getTier("cats"))

    def test_replace_tier_reports_if_new_tier_is_larger_than_textgrid(self):
        sut = textgrid.Textgrid(0, 5)
        tier1 = makeIntervalTier("words", intervals=[[1, 2, "hello"]])
        tier2 = makeIntervalTier("cats", intervals=[[3, 4, "goodbye"]])
        newTier1 = makeIntervalTier("phones", intervals=[[5, 6.7, "hey there"]])

        sut.addTier(tier1)
        sut.addTier(tier2)

        with self.assertRaises(errors.TextgridStateAutoModified) as _:
            sut.replaceTier("words", newTier1, "error")

    def test_replace_tier_throws_error_if_reporting_mode_is_invalid(self):
        sut = textgrid.Textgrid(0, 5)
        tier1 = makeIntervalTier("words", intervals=[[1, 2, "hello"]])
        tier2 = makeIntervalTier("cats", intervals=[[3, 4, "goodbye"]])
        newTier1 = makeIntervalTier("phones", intervals=[[5, 6.7, "hey there"]])

        sut.addTier(tier1)
        sut.addTier(tier2)

        with self.assertRaises(errors.WrongOption) as _:
            sut.replaceTier("words", newTier1, "cats")

    def test_validate_throws_error_if_reporting_mode_is_invalid(self):
        sut = textgrid.Textgrid()
        with self.assertRaises(errors.WrongOption) as _:
            sut.validate("bird")

    def test_validate_throws_error_if_tiers_and_textgrid_dont_agree_on_min_timestamp(
        self,
    ):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier(minT=1)

        sut.addTier(tier1)
        self.assertEqual(tier1.minTimestamp, sut.minTimestamp)
        self.assertTrue(sut.validate())

        sut.minTimestamp = 2.0
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))

        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_throws_error_if_tiers_and_textgrid_dont_agree_on_max_timestamp(
        self,
    ):
        sut = textgrid.Textgrid()
        tier1 = makeIntervalTier(maxT=10)

        sut.addTier(tier1)
        self.assertEqual(tier1.maxTimestamp, sut.maxTimestamp)
        self.assertTrue(sut.validate())

        sut.maxTimestamp = 12.0
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))

        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)

    def test_validate_throws_error_if_included_tier_is_invalid(
        self,
    ):
        sut = textgrid.Textgrid()

        tier = makeIntervalTier(intervals=[[0, 1, "hello"], [3, 4, "world"]])
        self.assertTrue(tier.validate())

        sut.addTier(tier)
        self.assertTrue(sut.validate())

        tier.maxTimestamp = 2.0
        self.assertFalse(tier.validate(constants.ErrorReportingMode.SILENCE))
        self.assertFalse(sut.validate(constants.ErrorReportingMode.SILENCE))

        with self.assertRaises(errors.TextgridStateError) as _:
            sut.validate(constants.ErrorReportingMode.ERROR)


if __name__ == "__main__":
    unittest.main()
