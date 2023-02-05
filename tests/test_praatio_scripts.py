import unittest

from praatio import textgrid
from praatio import praatio_scripts
from praatio.utilities.constants import Interval, Point, POINT_TIER
from praatio.utilities import constants
from praatio.utilities import errors

from tests.praatio_test_case import PraatioTestCase


class TestPraatioScripts(PraatioTestCase):
    def test_align_boundaries_across_tiers_works_for_interval_tiers(self):
        refTier = textgrid.IntervalTier("foo", [(0, 1, "hello"), (1, 2, "world")])

        targetIntervalTier = textgrid.IntervalTier(
            "bar", [(0, 0.5, "unchanged"), (1.001, 1.995, "changed")]
        )
        targetPointTier = textgrid.PointTier(
            "bizz", [(0.7, "unchanged"), (1.001, "changed 1"), (1.995, "changed 2")]
        )
        tg = textgrid.Textgrid()
        for tier in [refTier, targetIntervalTier, targetPointTier]:
            tg.addTier(tier)

        sut = praatio_scripts.alignBoundariesAcrossTiers(tg, "foo", maxDifference=0.01)

        self.assertEqual(
            [Interval(0, 1, "hello"), Interval(1, 2, "world")],
            sut.getTier("foo")._entries,
        )
        self.assertEqual(
            [Interval(0, 0.5, "unchanged"), Interval(1, 2, "changed")],
            sut.getTier("bar")._entries,
        )
        self.assertEqual(
            [Point(0.7, "unchanged"), Point(1, "changed 1"), Point(2, "changed 2")],
            sut.getTier("bizz")._entries,
        )

    def test_align_boundaries_across_tiers_works_for_point_tiers(self):
        refTier = textgrid.PointTier(
            "foo", [(0, "hello"), (1, "world"), (2, "goodbye")]
        )

        targetIntervalTier = textgrid.IntervalTier(
            "bar", [(0, 0.5, "unchanged"), (1.001, 1.995, "changed")]
        )
        targetPointTier = textgrid.PointTier(
            "bizz", [(0.7, "unchanged"), (1.001, "changed 1"), (1.995, "changed 2")]
        )
        tg = textgrid.Textgrid()
        for tier in [refTier, targetIntervalTier, targetPointTier]:
            tg.addTier(tier)

        sut = praatio_scripts.alignBoundariesAcrossTiers(tg, "foo", maxDifference=0.01)

        self.assertEqual(
            [Point(0, "hello"), Point(1, "world"), Point(2, "goodbye")],
            sut.getTier("foo")._entries,
        )
        self.assertEqual(
            [Interval(0, 0.5, "unchanged"), Interval(1, 2, "changed")],
            sut.getTier("bar")._entries,
        )
        self.assertEqual(
            [Point(0.7, "unchanged"), Point(1, "changed 1"), Point(2, "changed 2")],
            sut.getTier("bizz")._entries,
        )

    def test_align_boundaries_across_tiers_raises_error_if_max_difference_is_too_small(
        self,
    ):
        # In the reference tier we have a boundary at 1 and 1.0001, which is much smaller
        # than the maxDifference in this example so an exception will be thrown.
        refTier = textgrid.IntervalTier("foo", [(0, 1, "hello"), (1.0001, 2, "world")])

        targetTier = textgrid.IntervalTier(
            "bar", [(0, 0.5, "unchanged"), (1.001, 1.995, "changed")]
        )

        tg = textgrid.Textgrid()
        for tier in [refTier, targetTier]:
            tg.addTier(tier)

        with self.assertRaises(errors.ArgumentError) as _:
            praatio_scripts.alignBoundariesAcrossTiers(tg, "foo", maxDifference=0.01)
