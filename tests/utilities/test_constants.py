import unittest

from praatio.utilities import constants

from tests.praatio_test_case import PraatioTestCase


class TestConstants(PraatioTestCase):
    def test_interval_equivalence(self):
        self.assertEqual(
            constants.Interval(0.5555555556, 1.0, "hello"),
            constants.Interval(5 / 9.0, 1.0, "hello"),
        )

    def test_point_equivalence(self):
        self.assertEqual(
            constants.Point(0.5555555556, "hello"),
            constants.Point(5 / 9.0, "hello"),
        )
