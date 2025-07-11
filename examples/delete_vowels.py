"""
Praatio example for deleting the vowels from the textgrids and audio files.
"""

import os
from os.path import join
import copy
import wave

from praatio import textgrid
from praatio import audio
from praatio.utilities import utils


def isVowel(label):
    return any(
        [vowel in label.lower() for vowel in ["a", "e", "i", "o", "u", "ə", "œ"]]
    )


def deleteVowels(inputTGFN, inputWavFN, outputPath, doShrink, atZeroCrossing=True):

    utils.makeDir(outputPath)

    wavFN = os.path.split(inputWavFN)[1]
    tgFN = os.path.split(inputTGFN)[1]
    outputWavFN = join(outputPath, wavFN)
    outputTGFN = join(outputPath, tgFN)

    wav = audio.QueryWav(inputWavFN)

    if atZeroCrossing:
        zeroCrossingTGPath = join(outputPath, "zero_crossing_tgs")
        zeroCrossingTGFN = join(zeroCrossingTGPath, tgFN)
        utils.makeDir(zeroCrossingTGPath)

        tg = textgrid.openTextgrid(inputTGFN, False)

        outputTg = textgrid.Textgrid()
        for tier in tg.tiers:
            newTier = tier.toZeroCrossings(inputWavFN)
            outputTg.addTier(newTier)

        tg = outputTg

        outputTg.save(zeroCrossingTGFN, "short_textgrid", True)
    else:
        tg = textgrid.openTextgrid(inputTGFN, False)

    intervals = tg.getTier("phone").entries
    deleteIntervals = [(entry[0], entry[1]) for entry in intervals if isVowel(entry[2])]
    keepIntervals = utils.invertIntervalList(deleteIntervals, 0, wav.duration)

    wavReader = wave.open(inputWavFN, "r")
    replaceFunc = None
    if not doShrink:
        generator = audio.AudioGenerator.fromWav(wav)
        replaceFunc = generator.generateSilence

    frames = audio.readFramesAtTimes(
        wavReader, keepIntervals=keepIntervals, replaceFunc=replaceFunc
    )
    shrunkWav = audio.Wav(frames, wavReader.getparams())
    shrunkWav.save(outputWavFN)

    shrunkTG = copy.deepcopy(tg)
    for start, end in sorted(deleteIntervals, reverse=True):
        shrunkTG = shrunkTG.eraseRegion(start, end, doShrink=doShrink)

    shrunkTG.save(outputTGFN, "short_textgrid", True)


# Shrink files
root = join(".", "files")

inputTGFN = join(root, "bobby_phones.TextGrid")
inputWavFN = join(root, "bobby.wav")
outputPath = join(root, "deleted_test")

deleteVowels(inputTGFN, inputWavFN, outputPath, True, True)

inputTGFN = join(root, "mary.TextGrid")
inputWavFN = join(root, "mary.wav")
outputPath = join(root, "deleted_test")

deleteVowels(inputTGFN, inputWavFN, outputPath, True, True)

# Maintain original duration of files
inputTGFN = join(root, "bobby_phones.TextGrid")
inputWavFN = join(root, "bobby.wav")
outputPath = join(root, "deleted_test_no_shrinking")

deleteVowels(inputTGFN, inputWavFN, outputPath, False, True)

inputTGFN = join(root, "mary.TextGrid")
inputWavFN = join(root, "mary.wav")
outputPath = join(root, "deleted_test_no_shrinking")

deleteVowels(inputTGFN, inputWavFN, outputPath, False, True)
