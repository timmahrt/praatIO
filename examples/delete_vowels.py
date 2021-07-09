"""
Praatio example for deleting the vowels from the textgrids and audio files
"""

import os
from os.path import join
import copy

from praatio import textgrid
from praatio import praatio_scripts
from praatio import audio
from praatio.utilities import utils


def isVowel(label):
    return any([vowel in label.lower() for vowel in ["a", "e", "i", "o", "u"]])


def deleteVowels(inputTGFN, inputWavFN, outputPath, doShrink, atZeroCrossing=True):

    utils.makeDir(outputPath)

    wavFN = os.path.split(inputWavFN)[1]
    tgFN = os.path.split(inputTGFN)[1]
    outputWavFN = join(outputPath, wavFN)
    outputTGFN = join(outputPath, tgFN)

    if atZeroCrossing is True:
        zeroCrossingTGPath = join(outputPath, "zero_crossing_tgs")
        zeroCrossingTGFN = join(zeroCrossingTGPath, tgFN)
        utils.makeDir(zeroCrossingTGPath)

        tg = textgrid.openTextgrid(inputTGFN)
        wavObj = audio.WavQueryObj(inputWavFN)

        praatio_scripts.tgBoundariesToZeroCrossings(tg, wavObj, zeroCrossingTGFN)

    else:
        tg = textgrid.openTextgrid(inputTGFN)

    keepList = tg.tierDict["phone"].entryList
    keepList = [entry for entry in keepList if not isVowel(entry[2])]
    deleteList = utils.invertIntervalList(keepList, 0, tg.maxTimestamp)

    wavObj = audio.openAudioFile(inputWavFN, keepList=keepList, doShrink=doShrink)
    wavObj.save(outputWavFN)

    shrunkTG = copy.deepcopy(tg)
    for start, end in sorted(deleteList, reverse=True):
        shrunkTG = shrunkTG.eraseRegion(start, end, doShrink=doShrink)

    shrunkTG.save(outputTGFN)


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
