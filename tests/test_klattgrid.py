import unittest
from os.path import join

from praatio import klattgrid

from tests.testing_utils import areTheSameFiles
from tests.praatio_test_case import PraatioTestCase


class TestKlattgrid(PraatioTestCase):
    def test_reading_and_writing_klattgrids_does_not_mutate_file(self):
        """Tests for reading/writing klattgrids."""
        fn = "bobby.KlattGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        kg = klattgrid.openKlattgrid(inputFN)
        kg.save(outputFN)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, klattgrid.openKlattgrid))


if __name__ == "__main__":
    unittest.main()
