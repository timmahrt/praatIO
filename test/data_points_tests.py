import unittest
from os.path import join

from praatio import data_points

from test.testing_utils import areTheSameFiles
from test.praatio_test_case import PraatioTestCase


class DataPointsTest(PraatioTestCase):
    def test_duration_tier_io(self):
        """Tests for reading/writing duration tiers"""
        fn = "mary.DurationTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        dt = data_points.open2DPointObject(inputFN)
        dt.save(outputFN)

        self.assertTrue(
            areTheSameFiles(inputFN, outputFN, data_points.open2DPointObject)
        )

    def test_pitch_io(self):
        """Tests for reading/writing pitch tiers"""
        fn = "mary.PitchTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        pp = data_points.open2DPointObject(inputFN)
        pp.save(outputFN)

        self.assertTrue(
            areTheSameFiles(inputFN, outputFN, data_points.open2DPointObject)
        )

    def test_pitch_io_long_vs_short(self):
        """Tests reading of long vs short 2d point objects"""

        shortFN = join(self.dataRoot, "mary.PitchTier")
        longFN = join(self.dataRoot, "mary_longfile.PitchTier")

        self.assertTrue(areTheSameFiles(shortFN, longFN, data_points.open2DPointObject))

    def test_point_process_io(self):
        """Tests for reading/writing point processes"""
        fn = "bobby.PointProcess"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        pp = data_points.open1DPointObject(inputFN)
        pp.save(outputFN)

        self.assertTrue(
            areTheSameFiles(inputFN, outputFN, data_points.open1DPointObject)
        )

    def test_point_process_io_long_vs_short(self):

        shortFN = join(self.dataRoot, "bobby.PointProcess")
        longFN = join(self.dataRoot, "bobby_longfile.PointProcess")

        self.assertTrue(areTheSameFiles(shortFN, longFN, data_points.open1DPointObject))


if __name__ == "__main__":
    unittest.main()
