import unittest

from praatio import textgrid
from praatio.utilities.constants import Interval, Point, POINT_TIER, INTERVAL_TIER
from praatio.utilities import errors

from test.praatio_test_case import PraatioTestCase
from test import testing_utils


class PointTierTests(PraatioTestCase):
    def test_append_tier_with_mixed_type_throws_exception(self):
        pointTier = textgrid.PointTier(
            "pitch_values", [Point(1.3, "55"), Point(3.7, "99")], minT=0, maxT=5
        )
        intervalTier = textgrid.IntervalTier(
            "words",
            [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")],
            minT=0,
            maxT=5.0,
        )
        self.assertRaises(AssertionError, pointTier.appendTier, intervalTier)

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
        sut = textgrid.PointTier(
            "word_start",
            [
                Point(1, "hello"),
                Point(2.5, "the"),
                Point(3.5, "world"),
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

    def test_point_tier_creation_with_no_times(self):
        self.assertRaises(
            errors.TimelessTextgridTierException,
            textgrid.PointTier,
            "pitch_values",
            [],
            None,
            None,
        )

    def test_get_values_at_points_when_fuzzy_matching_is_false(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
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
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
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
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        sut.insertEntry(Point(0.5, "21"))

        self.assertEqual(
            [Point(0.5, "21"), Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_point_at_middle_of_point_tier(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        sut.insertEntry(Point(3.9, "21"))

        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99"), Point(3.9, "21"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_point_at_end_of_point_tier(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        sut.insertEntry(Point(4.9, "21"))

        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32"), Point(4.9, "21")],
            sut.entryList,
        )

    def test_insert_point_when_collision_occurs(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        self.assertRaises(
            errors.TextgridCollisionException,
            sut.insertEntry,
            Point(3.7, "hello"),
            False,
            None,
        )

    def test_insert_point_when_collision_occurs_and_merge(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        sut.insertEntry(Point(3.7, "hello"), False, textgrid.IntervalCollision.MERGE)
        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "99-hello"), Point(4.5, "32")],
            sut.entryList,
        )

    def test_insert_point_when_collision_occurs_and_replace(self):
        sut = textgrid.PointTier(
            "pitch_values",
            [Point(1.3, "55"), Point(3.7, "99"), Point(4.5, "32")],
            minT=0,
            maxT=5,
        )

        sut.insertEntry(Point(3.7, "hello"), False, textgrid.IntervalCollision.REPLACE)
        self.assertEqual(
            [Point(1.3, "55"), Point(3.7, "hello"), Point(4.5, "32")],
            sut.entryList,
        )


if __name__ == "__main__":
    unittest.main()
