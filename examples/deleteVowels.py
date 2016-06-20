'''
Created on June 20, 2016

@author: tmahrt

Deletes the vowels from the textgrids and audio files
'''

import os
from os.path import join

from praatio import tgio
from praatio import praatio_scripts
from praatio.utilities import utils


def isVowel(label):
    return any([vowel in label.lower() for vowel in ['a', 'e', 'i', 'o', 'u']])


def deleteVowels(inputTGFN, inputWavFN, outputPath, doShrink):
    
    utils.makeDir(outputPath)
    
    wavFN = os.path.split(inputWavFN)[1]
    tgFN = os.path.split(inputTGFN)[1]
    outputWavFN = join(outputPath, wavFN)
    outputTGFN = join(outputPath, tgFN)
    
    tg = tgio.openTextGrid(inputTGFN)
    deleteList = tg.tierDict["phone"].entryList
    deleteList = [entry for entry in deleteList
                  if not isVowel(entry[2])]
    
    praatio_scripts.deleteWavSections(inputWavFN, outputWavFN, deleteList, doShrink)
    
    for start, stop, _ in sorted(deleteList, reverse=True):
        tg.eraseRegion(start, stop, doShrink=doShrink)
    
    tg.save(outputTGFN)

# Shrink files
root = r"C:\Users\Tim\Dropbox\workspace\praatIO\examples\files"
inputTGFN = join(root, "bobby_phones.TextGrid")
inputWavFN = join(root, "bobby.wav")
outputPath = join(root, "deleted_test")

deleteVowels(inputTGFN, inputWavFN, outputPath, True)

inputTGFN = join(root, "mary.TextGrid")
inputWavFN = join(root, "mary.wav")
outputPath = join(root, "deleted_test")

deleteVowels(inputTGFN, inputWavFN, outputPath, True)

# Maintain original duration of files
inputTGFN = join(root, "bobby_phones.TextGrid")
inputWavFN = join(root, "bobby.wav")
outputPath = join(root, "deleted_test_no_shrinking")

deleteVowels(inputTGFN, inputWavFN, outputPath, False)

inputTGFN = join(root, "mary.TextGrid")
inputWavFN = join(root, "mary.wav")
outputPath = join(root, "deleted_test_no_shrinking")

deleteVowels(inputTGFN, inputWavFN, outputPath, False)
