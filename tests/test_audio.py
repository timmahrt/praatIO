import unittest
from os.path import join
import tempfile
import wave

from praatio import audio
from praatio.utilities import utils
from praatio.utilities import errors

from tests.praatio_test_case import PraatioTestCase

# Wrap superclasses in a dummy test to prevent them from running
# https://stackoverflow.com/a/25695512
class AudioWrapper:
    class TestAudio(PraatioTestCase):
        def test_get_audio_duration(self):
            """Tests that the two audio duration methods output the same value."""
            durationA = utils.getWavDuration(self.bobWavFN)
            durationB = audio.getDuration(self.bobWavFN)
            self.assertEqual(1.194625, durationA)
            self.assertEqual(durationA, durationB)

        def test_extract_subwavs(self):
            """Tests that extractSubwavs will output files with the expected duration"""
            outputWavFN = join(self.outputRoot, "bobby_word.wav")

            audio.extractSubwav(self.bobWavFN, outputWavFN, 0.06, 0.40)

            duration = utils.getWavDuration(outputWavFN)
            self.assertEqual(0.34, duration)

        def test_query_wav_duration(self):
            wav = audio.QueryWav(self.bobWavFN)

            self.assertEqual(1.194625, wav.duration)

        def test_query_wav_get_frames(self):
            wav = audio.QueryWav(self.bobWavFN)
            wavObj = wave.open(self.bobWavFN, "r")

            self.assertEqual(
                audio.readFramesAtTime(wavObj, 0.5, 1.12), wav.getFrames(0.5, 1.12)
            )

        def test_query_wav_get_frames_defaults_to_all_frames(self):
            wav = audio.QueryWav(self.bobWavFN)
            wavObj = wave.open(self.bobWavFN, "r")
            expectedFrames = audio.readFramesAtTime(wavObj, 0, wav.duration)

            self.assertEqual(expectedFrames, wav.getFrames())

        def test_query_wav_get_samples(self):
            wav = audio.QueryWav(self.bobWavFN)
            wavObj = wave.open(self.bobWavFN, "r")

            self.assertEqual(
                audio.convertFromBytes(
                    audio.readFramesAtTime(wavObj, 0.5, 1.12), wavObj.getsampwidth()
                ),
                wav.getSamples(0.5, 1.12),
            )

        def test_wav_open(self):
            # The open() method should have the same result as
            # as manually creating a Wav
            sut = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            frames = audio.readFramesAtTime(wav, 0, audio.getDuration(self.bobWavFN))
            wavObj = audio.Wav(frames, wav.getparams())

            self.assertEqual(wavObj, sut)

        def test_wav_equal_to_non_wav_is_false(self):
            sut = audio.Wav.open(self.bobWavFN)
            wav = audio.QueryWav(self.bobWavFN)

            self.assertNotEqual(5, sut)
            self.assertNotEqual(wav, sut)  # QueryWavs are not Wavs

        def test_wav_new_creates_a_unique_copy(self):
            wav = audio.Wav.open(self.bobWavFN)
            sut = wav.new()

            self.assertEqual(wav, sut)

            sut.deleteSegment(0.5, 1.0)

            self.assertNotEqual(wav, sut)

        def test_wav_concatenate(self):
            expectedWav = audio.Wav.open(self.bobWavFN)
            wav = wave.open(self.bobWavFN, "r")
            firstHalfFrames = audio.readFramesAtTime(wav, 0.0, 0.7)
            lastHalfFrames = audio.readFramesAtTime(
                wav, 0.7, audio.getDuration(self.bobWavFN)
            )

            sut = audio.Wav(firstHalfFrames, wav.getparams())
            sut.concatenate(lastHalfFrames)

            self.assertEqual(expectedWav, sut)

        def test_wav_delete_segment(self):
            sut = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            expectedFrames = audio.readFramesAtTime(wav, 0.25, 0.93)

            sut.deleteSegment(0.93, sut.duration)
            sut.deleteSegment(0, 0.25)

            self.assertEqual(expectedFrames, sut.frames)

        def test_wav_duration(self):
            fullWavFile = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            subsegmentFrames = audio.readFramesAtTime(wav, 0.25, 0.93)
            wavSubsegment = audio.Wav(subsegmentFrames, wav.getparams())

            self.assertEqual(1.194625, fullWavFile.duration)
            self.assertEqual(0.68, wavSubsegment.duration)

        def test_wav_get_frames(self):
            wavObj = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            expectedFrames = audio.readFramesAtTime(wav, 0.25, 0.93)

            sut = wavObj.getFrames(0.25, 0.93)

            self.assertEqual(expectedFrames, sut)

        def test_wav_get_samples(self):
            # This test isn't really testing anything since there is
            # only a single way the methods convert from bytes
            wavObj = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            expectedFrames = audio.readFramesAtTime(wav, 0.25, 0.93)
            expectedSamples = audio.convertFromBytes(expectedFrames, wav.getsampwidth())

            sut = wavObj.getSamples(0.25, 0.93)

            self.assertEqual(expectedSamples, sut)

        def test_wav_get_subwav(self):
            wavObj = audio.Wav.open(self.bobWavFN)

            sut = wavObj.getSubwav(0.25, 0.93)

            wav = wave.open(self.bobWavFN, "r")
            expectedFrames = audio.readFramesAtTime(wav, 0.25, 0.93)
            expectedSubwav = audio.Wav(expectedFrames, wav.getparams())

            self.assertEqual(expectedSubwav, sut)

        def test_wav_insert(self):
            expectedWav = audio.Wav.open(self.bobWavFN)

            wav = wave.open(self.bobWavFN, "r")
            firstThirdFrames = audio.readFramesAtTime(wav, 0.0, 0.25)
            secondThirdFrames = audio.readFramesAtTime(wav, 0.25, 0.93)
            finalThirdFrames = audio.readFramesAtTime(wav, 0.93, expectedWav.duration)

            sut = audio.Wav(finalThirdFrames, expectedWav.params)
            sut.insert(0, firstThirdFrames)
            sut.insert(0.25, secondThirdFrames)

            self.assertEqual(expectedWav, sut)

        def test_wav_replace_segment_with_segment_of_equal_length(self):
            sut = audio.Wav.open(self.bobWavFN)

            sut.replaceSegment(0.5, 1.0, sut.getFrames(0.0, 0.5))

            self.assertEqual(1.194625, sut.duration)

        def test_wav_replace_segment_with_segment_of_non_equal_length(self):
            expectedDuration = audio.getDuration(self.bobWavFN) + 0.5
            sut = audio.Wav.open(self.bobWavFN)

            sut.replaceSegment(0.5, 1.0, sut.getFrames(0.0, 1.0))

            self.assertEqual(expectedDuration, sut.duration)

        def test_open_audio_with_keep_list(self):
            wav = wave.open(self.bobWavFN, "r")

            sut = audio.readFramesAtTimes(
                wav, keepIntervals=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")]
            )

            sut.save(join(self.outputRoot, "bobby_word_tmp.wav"))
            self.assertEqual(0.34 + 0.37, sut.duration)

        def test_open_audio_with_keep_intervals_and_deleted_segments_are_replaced_with_silence(
            self,
        ):
            expectedDuration = audio.getDuration(self.bobWavFN)
            wavObj = wave.open(self.bobWavFN, "r")

            wav = audio.Wav.open(self.bobWavFN)
            generator = audio.AudioGenerator(wav.sampleWidth, wav.frameRate)

            sut = audio.readFramesAtTimes(
                wavObj,
                keepIntervals=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")],
                replaceFunc=generator.generateSilence,
            )

            sut.save(join(self.outputRoot, "bobby_word_keep_intervals_and_silence.wav"))
            self.assertEqual(expectedDuration, sut.duration)

        def test_open_audio_with_delete_intervals(self):
            start1, end1 = (0.06, 0.40)
            start2, end2 = (0.75, 1.12)
            expectedDuration = (
                audio.getDuration(self.bobWavFN) - (end1 - start1) - (end2 - start2)
            )
            wav = wave.open(self.bobWavFN, "r")

            sut = audio.readFramesAtTimes(
                wav, deleteIntervals=[(start1, end1, "Bobby"), (start2, end2, "Ledger")]
            )

            self.assertAlmostEqual(expectedDuration, sut.duration, 4)

        def test_open_audio_with_deleted_segments_replaced_with_silence(self):
            expectedDuration = audio.getDuration(self.bobWavFN)
            wavObj = wave.open(self.bobWavFN, "r")

            wav = audio.Wav.open(self.bobWavFN)
            generator = audio.AudioGenerator(wav.sampleWidth, wav.frameRate)

            sut = audio.readFramesAtTimes(
                wavObj,
                deleteIntervals=[(0.06, 0.40, "Bobby"), (0.75, 1.12, "Ledger")],
                replaceFunc=generator.generateSilence,
            )

            sut.save(join(self.outputRoot, "bobby_word_delete_list_and_silence.wav"))
            self.assertEqual(expectedDuration, sut.duration)


class TestAudioWith16Bits48000Hz(AudioWrapper.TestAudio):
    def __init__(self, *args, **kargs):
        super(AudioWrapper.TestAudio, self).__init__(*args, **kargs)

        self.bobWavFN = join(self.dataRoot, "bobby_16bit_48khz.wav")

        wav = wave.open(self.bobWavFN, "r")
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 48_000


class TestAudioWith32Bits48000Hz(AudioWrapper.TestAudio):
    def __init__(self, *args, **kargs):
        super(AudioWrapper.TestAudio, self).__init__(*args, **kargs)

        self.bobWavFN = join(self.dataRoot, "bobby_32bit_48khz.wav")

        wav = wave.open(self.bobWavFN, "r")
        assert wav.getsampwidth() == 4
        assert wav.getframerate() == 48_000


class TestAudioWith16Bits16000Hz(AudioWrapper.TestAudio):
    def __init__(self, *args, **kargs):
        super(AudioWrapper.TestAudio, self).__init__(*args, **kargs)

        self.bobWavFN = join(self.dataRoot, "bobby_16bit_16khz.wav")

        wav = wave.open(self.bobWavFN, "r")
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16_000


class TestAudioWith32Bits16000Hz(AudioWrapper.TestAudio):
    def __init__(self, *args, **kargs):
        super(AudioWrapper.TestAudio, self).__init__(*args, **kargs)

        self.bobWavFN = join(self.dataRoot, "bobby_32bit_16khz.wav")

        wav = wave.open(self.bobWavFN, "r")
        assert wav.getsampwidth() == 4
        assert wav.getframerate() == 16_000


class TestAudio(PraatioTestCase):
    def test_wav_open_fails_when_there_are_more_than_2_channels(self):
        self.bobWavFN = join(self.dataRoot, "bobby_16bit_16khz_2ch.wav")

        wav = wave.open(self.bobWavFN, "r")
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16_000
        assert wav.getnchannels() == 2

        with self.assertRaises(errors.ArgumentError) as _:
            audio.Wav.open(self.bobWavFN)

    def test_calculate_max_amplitude(self):
        self.assertEqual(127, audio.calculateMaxAmplitude(1))
        self.assertEqual(32_767, audio.calculateMaxAmplitude(2))
        self.assertEqual(8_388_607, audio.calculateMaxAmplitude(3))
        self.assertEqual(2_147_483_647, audio.calculateMaxAmplitude(4))

    def test_convert_to_and_from_bytes_when_sample_width_is_one(self):
        values = (0, 10, 90, 127, 0, -10, -90, -127)
        valuesAsBytes = audio.convertToBytes(values, 1)
        sut = audio.convertFromBytes(valuesAsBytes, 1)

        self.assertEqual(values, sut)

    def test_convert_to_and_from_bytes_when_sample_width_is_four(self):
        values = (
            0,
            483_647,
            147_483_647,
            2_147_483_647,
            0,
            -483_647,
            -147_483_647,
            -2_147_483_647,
        )
        valuesAsBytes = audio.convertToBytes(values, 4)
        sut = audio.convertFromBytes(valuesAsBytes, 4)

        self.assertEqual(values, sut)

    def test_audio_generator_build_sine_wave_generator(self):
        generator = audio.AudioGenerator(2, 16_000)

        sineGenerator = generator.buildSineWaveGenerator(100, 10_000)

        sineWav = sineGenerator(1.0)
        sut = audio.convertFromBytes(sineWav, 2)
        maxValue = 10_000  # Set by the method call

        self.assertEqual(16_000, len(sut))
        self.assertEqual(maxValue * -1, min(sut))
        self.assertEqual(maxValue, max(sut))
        self.assertEqual(100, sut.count(maxValue * -1))
        self.assertEqual(100, sut.count(maxValue))
        self.assertEqual(200, sut.count(0))

    def test_audio_generator_generate_sine_wave_of_100hz(self):
        generator = audio.AudioGenerator(2, 16_000)

        sineWav = generator.generateSineWave(1.0, 100)
        sut = audio.convertFromBytes(sineWav, 2)
        maxValue = 32767  # From the sample width

        self.assertEqual(16_000, len(sut))
        self.assertEqual(maxValue * -1, min(sut))
        self.assertEqual(maxValue, max(sut))
        self.assertEqual(100, sut.count(maxValue * -1))
        self.assertEqual(100, sut.count(maxValue))
        self.assertEqual(200, sut.count(0))

    def test_audio_generator_generate_sine_wave_with_set_amplitude(self):
        generator = audio.AudioGenerator(2, 16_000)

        sineWav = generator.generateSineWave(1.0, 100, 10_000)
        sut = audio.convertFromBytes(sineWav, 2)
        maxValue = 10_000  # Set by the method call

        self.assertEqual(16_000, len(sut))
        self.assertEqual(maxValue * -1, min(sut))
        self.assertEqual(maxValue, max(sut))
        self.assertEqual(100, sut.count(maxValue * -1))
        self.assertEqual(100, sut.count(maxValue))
        self.assertEqual(200, sut.count(0))

    def test_audio_generator_generate_sine_wave_of_400hz(self):
        generator = audio.AudioGenerator(2, 16_000)

        sineWav = generator.generateSineWave(1.0, 400)
        sut = audio.convertFromBytes(sineWav, 2)
        maxValue = 32767  # From the sample width

        self.assertEqual(16_000, len(sut))
        self.assertEqual(maxValue * -1, min(sut))
        self.assertEqual(maxValue, max(sut))
        self.assertEqual(400, sut.count(maxValue * -1))
        self.assertEqual(400, sut.count(maxValue))
        self.assertEqual(800, sut.count(0))

    def test_audio_generator_generate_silence(self):
        generator = audio.AudioGenerator(2, 16_000)

        silence = generator.generateSilence(1.0)
        sut = audio.convertFromBytes(silence, 2)

        self.assertEqual(16_000, len(sut))
        self.assertEqual(0, min(sut))
        self.assertEqual(0, max(sut))

    def test_wav_find_nearest_zero_crossing(self):
        numChannels = 1
        sampleWidth = 2
        frameRate = 16_000
        generator = audio.AudioGenerator(sampleWidth, frameRate)

        # zero crossings occur at 0 and 0.5 (and almost at 1.0 -- off by one sample)
        sineWavFrames = generator.generateSineWave(1.0, 1)
        sineWav = audio.Wav(
            sineWavFrames,
            [numChannels, sampleWidth, frameRate, 16_000, "unused", "unused"],
        )

        # Should return the specified time if its a zero crossing
        self.assertAlmostEqual(0, sineWav.findNearestZeroCrossing(0))
        self.assertAlmostEqual(0.5, sineWav.findNearestZeroCrossing(0.5))

        # If equidistant, it should choose the one on the left
        self.assertAlmostEqual(0.0, sineWav.findNearestZeroCrossing(0.24))
        self.assertAlmostEqual(0.0, sineWav.findNearestZeroCrossing(0.25))
        self.assertAlmostEqual(0.5, sineWav.findNearestZeroCrossing(0.26))

        self.assertAlmostEqual(0.5, sineWav.findNearestZeroCrossing(0.4))
        self.assertAlmostEqual(0.5, sineWav.findNearestZeroCrossing(0.6))
        self.assertAlmostEqual(0.5, sineWav.findNearestZeroCrossing(1.0))

    def test_wav_find_nearest_zero_crossing_throws_argument_error(self):
        # With a sampling rate of 1 frame per second and a step size of
        # 1 second, findNearestZeroCrossing won't have a large enough
        # sample size to work with and will throw an exception
        sampleWidth = 2
        samples = [5, 10, 20, 15, 0, -1, -7, -3, 0, 10]
        frames = audio.convertToBytes(samples, sampleWidth)
        params = [1, sampleWidth, 1, len(samples), "", ""]  # 1 frame per second
        sut = audio.Wav(frames, params)

        with self.assertRaises(errors.ArgumentError) as _:
            sut.findNearestZeroCrossing(0, 1)

    def test_wav_find_nearest_zero_crossing_with_simple_cases(self):
        sampleWidth = 2
        samples = [5, 10, 20, 15, 0, -1, -7, -3, 0, 10]
        frames = audio.convertToBytes(samples, sampleWidth)
        params = [1, sampleWidth, 1, len(samples), "", ""]  # 1 frame per second
        sut = audio.Wav(frames, params)

        self.assertEqual(4, sut.findNearestZeroCrossing(0, 2))
        self.assertEqual(8, sut.findNearestZeroCrossing(9, 2))

    def test_wav_find_nearest_zero_crossing_when_there_is_no_zero_value(self):
        sampleWidth = 2
        samples = [10, 20, 1, -5, -7, -3, -1, 3, 10, 4]
        frames = audio.convertToBytes(samples, sampleWidth)
        params = [1, sampleWidth, 1, len(samples), "", ""]  # 1 frame per second
        sut = audio.Wav(frames, params)

        self.assertEqual(2, sut.findNearestZeroCrossing(0, 2))
        self.assertEqual(6, sut.findNearestZeroCrossing(9, 2))

    def test_wav_find_nearest_zero_crossing_chooses_the_smaller_value_at_zero_crossing(
        self,
    ):
        sampleWidth = 2
        samples = [10, 20, 15, -1, -7, -3, -2, 1, 10, 4]
        frames = audio.convertToBytes(samples, sampleWidth)
        params = [1, sampleWidth, 1, len(samples), "", ""]  # 1 frame per second
        sut = audio.Wav(frames, params)

        # abs(15) is larger than abs(-1), so although the zero crossing
        # is at 15, we choose -1, since its closer to zero
        self.assertEqual(3, sut.findNearestZeroCrossing(0, 2))

        # abs(-2) is larger than abs(1), so although the zero crossing
        # is at -2, we choose -1 since its closer to zero
        self.assertEqual(7, sut.findNearestZeroCrossing(9, 2))


if __name__ == "__main__":
    unittest.main()
