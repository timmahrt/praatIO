import unittest

from praatio.utilities import constants

from tests.praatio_test_case import PraatioTestCase


class TestConstants(PraatioTestCase):
    def test_interval_as_named_tuple(self):
        sut = constants.Interval(0.5, 1, "hello")

        self.assertEqual(0.5, sut[0])
        self.assertEqual(0.5, sut.start)

        self.assertEqual(1, sut[1])
        self.assertEqual(1, sut.end)

        self.assertEqual("hello", sut[2])
        self.assertEqual("hello", sut.label)

    def test_interval_equivalence(self):
        self.assertEqual(
            constants.Interval(0.5555555556, 1.0, "hello"),
            constants.Interval(5 / 9.0, 1.0, "hello"),
        )
        self.assertNotEqual(
            constants.Interval(5 / 9.0, 1.0, "hello"), (0.5555555556, 1.0, "hello")
        )
        self.assertNotEqual(constants.Interval(5 / 9.0, 1.0, "hello"), "hello")

    def test_point_as_named_tuple(self):
        sut = constants.Point(0.5, "hello")

        self.assertEqual(0.5, sut[0])
        self.assertEqual(0.5, sut.time)

        self.assertEqual("hello", sut[1])
        self.assertEqual("hello", sut.label)

    def test_point_equivalence(self):
        self.assertEqual(
            constants.Point(0.5555555556, "hello"),
            constants.Point(5 / 9.0, "hello"),
        )

        self.assertNotEqual(constants.Point(5 / 9.0, "hello"), (5 / 9.0, "hello"))
        self.assertNotEqual(constants.Point(5 / 9.0, "hello"), "hello")


if __name__ == "__main__":
    unittest.main()
