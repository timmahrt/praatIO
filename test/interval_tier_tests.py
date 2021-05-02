import unittest

from praatio import textgrid
from praatio.utilities.constants import Interval, Point, POINT_TIER, INTERVAL_TIER
from praatio.utilities import errors

from test.praatio_test_case import PraatioTestCase
from test import testing_utils


class IntervalTierTests(PraatioTestCase):
    intervalTier = textgrid.IntervalTier(
        "words",
        [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")],
        minT=0,
        maxT=5.0,
    )

    def test_append_tier_with_interval_tiers(self):
        intervalTier2 = textgrid.IntervalTier(
            "new_words",
            [Interval(1, 2.5, "hi"), Interval(4.1, 4.8, "planet")],
            minT=0,
            maxT=7,
        )
        sut = self.intervalTier.appendTier(intervalTier2)
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
        sut = textgrid.IntervalTier(
            "words",
            [
                Interval(1, 2, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=5.0,
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
            AssertionError,
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
        sut = textgrid.IntervalTier(
            "pitch_values",
            [
                Interval(1, 2.5, "hello"),
                Interval(2.5, 3.0, "the"),
                Interval(3.5, 4.0, "world"),
            ],
            minT=0,
            maxT=4,
        )

        self.assertEqual(
            [Interval(0, 1, ""), Interval(3.0, 3.5, "")],
            sut.getNonEntries(),
        )

    def test_interval_tier_morph_when_shrinking_intervals(self):
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

    def test_interval_tier_morph_when_growing_intervals(self):
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

    def test_interval_tier_morph_when_tiers_have_different_numbers_of_intervals(self):
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

        self.assertRaises(AssertionError, sourceTier.morph, targetTier)

    def test_interval_tier_mintimestamp_behaviour(self):
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
