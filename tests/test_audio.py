import unittest
from os.path import join
import tempfile

from praatio import audio
from praatio.utilities import utils

from tests.praatio_test_case import PraatioTestCase


class TestAudio(PraatioTestCase):
    def test_get_audio_duration(self):
        """Tests that the two audio duration methods output the same value."""
        wavFN = join(self.dataRoot, "bobby.wav")

        durationA = utils.getWavDuration(wavFN)
        durationB = audio.getDuration(wavFN)
        self.assertEqual(durationA, durationB)

    def test_extract_subwavs(self):
        """Tests that extractSubwavs will output files with the expected duration"""
        wavFN = join(self.dataRoot, "bobby.wav")
        outputWavFN = join(self.outputRoot, "bobby_word.wav")

        audio.extractSubwav(wavFN, outputWavFN, 0.06, 0.40)

        duration = utils.getWavDuration(outputWavFN)
        self.assertEqual(0.34, duration)

    def test_open_audio_with_keep_list(self):
        wavFN = join(self.dataRoot, "bobby.wav")

        sut = audio.openAudioFile(
            wavFN, keepList=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")]
        )

        sut.save(join(self.outputRoot, "bobby_word_tmp.wav"))
        self.assertEqual(0.34 + 0.37, sut.duration)

    def test_open_audio_with_keep_list_and_do_shrink_is_false(self):
        wavFN = join(self.dataRoot, "bobby.wav")
        expectedDuration = audio.getDuration(wavFN)

        sut = audio.openAudioFile(
            wavFN,
            keepList=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")],
            doShrink=False,
        )

        sut.save(join(self.outputRoot, "bobby_word_keep_list_do_shrink_is_false.wav"))
        self.assertEqual(expectedDuration, sut.duration)

    def test_open_audio_with_delete_list(self):
        wavFN = join(self.dataRoot, "bobby.wav")
        expectedDuration = audio.getDuration(wavFN) - 0.34 - 0.37

        sut = audio.openAudioFile(
            wavFN, deleteList=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")]
        )

        self.assertAlmostEqual(expectedDuration, sut.duration, 4)

    def test_open_audio_with_delete_list_and_do_shrink_is_false(self):
        wavFN = join(self.dataRoot, "bobby.wav")
        expectedDuration = audio.getDuration(wavFN)

        sut = audio.openAudioFile(
            wavFN,
            deleteList=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")],
            doShrink=False,
        )

        sut.save(join(self.outputRoot, "bobby_word_delete_list_do_shrink_is_false.wav"))
        self.assertEqual(expectedDuration, sut.duration)

    def test_blah(self):
        wavFN = join(self.dataRoot, "bobby.wav")
        durations = []
        i = 0
        for deleteList, name in [
            [
                [
                    (0.1, 0.11, "a"),
                    (0.4, 0.6, "b"),
                    (0.8, 1.0, "c"),
                    (1.01, 1.04, "d"),
                ],
                "bobby_4.wav",
            ],
            [[(0.1, 0.3, "a")], "bobby_1.wav"],
            [[(0.1, 0.3, "a"), (0.4, 0.6, "b")], "bobby_2.wav"],
            [[(0.1, 0.3, "a"), (0.4, 0.6, "b"), (0.8, 1.0, "c")], "bobby_3.wav"],
            [
                [(0.1, 0.3, "a"), (0.4, 0.6, "b"), (0.8, 1.0, "c"), (1.01, 1.04, "d")],
                "bobby_4.wav",
            ],
        ]:
            sut = audio.openAudioFile(
                wavFN,
                deleteList=deleteList,
                doShrink=False,
            )

            sut.save(join(self.outputRoot, name))
            print([i, sut.duration])
            i += 1
            durations.append(sut.duration)
        print(sut.duration)
        self.assertEqual(1, 2)


if __name__ == "__main__":
    unittest.main()
