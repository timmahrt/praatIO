import unittest
from os.path import join

from praatio import audio
from praatio.utilities import utils

from tests.praatio_test_case import PraatioTestCase


class TestAudio(PraatioTestCase):
    def test_get_audio_duration(self):
        """Tests that the two audio duration methods output the same value."""
        wavFN = join(self.dataRoot, "bobby.wav")

        durationA = utils.getWavDuration(wavFN)
        durationB = audio.getDuration(wavFN)
        self.assertTrue(durationA == durationB)


if __name__ == "__main__":
    unittest.main()
