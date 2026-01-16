import unittest
from os.path import join

from praatio import data_points
from praatio.utilities import constants

from tests.testing_utils import areTheSameFiles
from tests.praatio_test_case import PraatioTestCase


# Create a custom float class that overrides the __repr__ method
# similar to how Numpy.float64 overrides the __repr__ method
class CustomFloat(float):
    def __init__(self, value):
        self.value = value

    def __float__(self):
        return self.value

    def __repr__(self):
        return f"CustomFloat({self.value})"


class TestDataPoint(PraatioTestCase):
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

    def test_point_object_1d_creation_with_custom_float(self):
        sut = data_points.PointObject1D(
            pointList=[
                (CustomFloat(1.0),),
                (CustomFloat(3.0),),
            ],
            objectClass=constants.DataPointTypes.POINT,
            minTime=1,
            maxTime=4,
        )
        self.assertEqual([(1.0,), (3.0,)], sut.pointList)
        self.assertEqual("1.0", repr(sut.pointList[0][0]))
        self.assertEqual("3.0", repr(sut.pointList[1][0]))

    def test_point_object_2d_creation_with_custom_float(self):
        sut = data_points.PointObject2D(
            pointList=[
                (CustomFloat(1.0), CustomFloat(2.0)),
                (CustomFloat(3.0), CustomFloat(4.0)),
            ],
            objectClass=constants.DataPointTypes.PITCH,
            minTime=1,
            maxTime=4,
        )
        self.assertEqual([(1.0, 2.0), (3.0, 4.0)], sut.pointList)
        self.assertEqual("1.0", repr(sut.pointList[0][0]))
        self.assertEqual("2.0", repr(sut.pointList[0][1]))
        self.assertEqual("3.0", repr(sut.pointList[1][0]))
        self.assertEqual("4.0", repr(sut.pointList[1][1]))


if __name__ == "__main__":
    unittest.main()
