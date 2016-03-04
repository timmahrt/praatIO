'''
Created on Jan 5, 2016

@author: tmahrt

Extracts pitch and intensity values in a wav file using praat
'''

import os
from os.path import join

from praatio import pitch_and_intensity
from praatio import tgio
from praatio import common

wavPath = os.path.abspath(join(".", "files"))
tgPath = os.path.abspath(join(".", "files"))
rootOutputFolder = os.path.abspath(join(".", "files", "pitch_extraction"))
pitchPath = join(rootOutputFolder, "pitch")
pitchMeasuresPath = join(rootOutputFolder, "pitch_measures")
rmsIntensityPath = join(rootOutputFolder, "rms_intensity")


praatEXE = r"C:\Praat.exe"
#praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"
common.makeDir(rootOutputFolder)


bobbyPitchData = pitch_and_intensity.audioToPI(wavPath, "bobby.wav", pitchPath, 
                                               "bobby.txt", praatEXE, 50, 350,
                                               forceRegenerate=False)

maryPitchData = pitch_and_intensity.audioToPI(wavPath, "mary.wav", pitchPath,
                                              "mary.txt", praatEXE, 75, 450,
                                              forceRegenerate=False)

filteredFN = "mary_300hz_high_pass_filtered.wav"
maryFilteredPitchData = pitch_and_intensity.audioToPI(wavPath, filteredFN,
                                                      pitchPath, "mary_filtered.txt",
                                                      praatEXE, 75, 450,
                                                      forceRegenerate=False)

# Generate pitch and intensity values for one file
pitch_and_intensity.generatePIMeasures(bobbyPitchData, tgPath,
                                       "bobby_words.TextGrid", 
                                       "word", doPitch=True)

pitch_and_intensity.generatePIMeasures(maryPitchData, tgPath,
                                       "mary.TextGrid", 
                                       "word", doPitch=False)

tg = tgio.openTextGrid(join(tgPath, "bobby_words.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, 1.0, tg)[1]
tg.save(join(rootOutputFolder, "bobby_errors.TextGrid"))

tg = tgio.openTextGrid(join(tgPath, "mary.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, 1.0, tg)[1]
tg.save(join(rootOutputFolder, "mary_errors.TextGrid"))

tg = tgio.openTextGrid(join(tgPath, "mary.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(maryFilteredPitchData, 0.75, 1.0, tg)[1]
tg.save(join(rootOutputFolder, "mary_filtered_errors.TextGrid"))
