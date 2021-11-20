import unittest

from praatio.utilities import my_math

from test.praatio_test_case import PraatioTestCase


class MyMathTests(PraatioTestCase):

    datasetA = [1, 10, 100, 1000]
    datasetB = [1, -10, 100, -1000]
    datasetC = [10.5, 47, 93.24, -5]
    datasetD = [32, 24, 18, 5, 61]

    def test_rms(self):
        self.assertAlmostEqual(502.518905117, my_math.rms(self.datasetA))
        self.assertAlmostEqual(502.518905117, my_math.rms(self.datasetB))
        self.assertAlmostEqual(52.5308185735, my_math.rms(self.datasetC))
        self.assertAlmostEqual(33.6749164809, my_math.rms(self.datasetD))

    def test_znormalize_data(self):
        self.assertAllAlmostEqual(
            [
                -0.5723056009616835,
                -0.553694036702767,
                -0.3675783941136016,
                1.493578031778052,
            ],
            my_math.znormalizeData(self.datasetA),
        )
        self.assertAllAlmostEqual(
            [
                0.441032062,
                0.419777504,
                0.632323077,
                -1.49313264,
            ],
            my_math.znormalizeData(self.datasetB),
        )
        self.assertAllAlmostEqual(
            [
                -0.593538316,
                0.2417864781,
                1.3000171219,
                -0.948265283,
            ],
            my_math.znormalizeData(self.datasetC),
        )
        self.assertAllAlmostEqual(
            [
                0.191236577,
                -0.191236577,
                -0.478091443,
                -1.099610320,
                1.577701764,
            ],
            my_math.znormalizeData(self.datasetD),
        )

    def test_median_filter(self):
        dataset = [1, 10, 1, 9, 5, 2, 4, 7, 4, 5, 10, 5]
        self.assertEqual(
            [1, 1, 9, 5, 5, 4, 4, 4, 5, 5, 5, 5],
            my_math.medianFilter(dataset, 3, False),
        )
        self.assertEqual(
            [1, 1, 9, 5, 5, 4, 4, 4, 5, 5, 5, 5],
            my_math.medianFilter(dataset, 3, True),
        )
        self.assertEqual(
            [1, 10, 5, 5, 4, 5, 4, 4, 5, 5, 10, 5],
            my_math.medianFilter(dataset, 5, False),
        )
        self.assertEqual(
            [1, 1, 5, 5, 4, 5, 4, 4, 5, 5, 5, 5],
            my_math.medianFilter(dataset, 5, True),
        )


if __name__ == "__main__":
    unittest.main()
