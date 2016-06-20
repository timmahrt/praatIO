'''
Created on Jan 5, 2016

@author: tmahrt

Extracts pitch and intensity values in a wav file using praat
'''

import os
from os.path import join

from praatio import pitch_and_intensity
from praatio import praat_scripts
from praatio import tgio
from praatio.utilities import utils

wavPath = os.path.abspath(join(".", "files"))
tgPath = os.path.abspath(join(".", "files"))
rootOutputFolder = os.path.abspath(join(".", "files", "pitch_extraction"))
pitchPath = join(rootOutputFolder, "pitch")
formantsPath = join(rootOutputFolder, "formants")
pitchMeasuresPath = join(rootOutputFolder, "pitch_measures")
rmsIntensityPath = join(rootOutputFolder, "rms_intensity")


praatEXE = r"C:\Praat.exe"
#praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"
utils.makeDir(rootOutputFolder)
utils.makeDir(pitchPath)
utils.makeDir(pitchMeasuresPath)
utils.makeDir(rmsIntensityPath)
utils.makeDir(formantsPath)

bobbyPitchData = pitch_and_intensity.audioToPI(wavPath, "bobby.wav", pitchPath,
                                               "bobby.txt", praatEXE, 50, 350,
                                               forceRegenerate=False)

# Here are two examples of the new functionality of extracting pitch
# from only labeled intervals in a textgrid.  However, the example files
# I have provided are too short and praat will not process them.

# Extracts each labeled interval as a separate wave file, extracts the
# pitch track from each of those, and then aggregates the result.
# pitch_and_intensity.audioToPI(wavPath, "bobby.wav", pitchPath,
#                              "bobby_segments.txt", praatEXE,
#                              50, 350,
#                              forceRegenerate=True,
#                              tgPath=wavPath,
#                              tgFN="bobby_words.TextGrid",
#                              tierName="word")

# Generates the entire pitch contour for the file, but only saves the
# labeled sections.  Functionally the same as the commented-out code above.
# pitch_and_intensity._audioToPIFile(wavPath, "bobby.wav", pitchPath,
#                                    "bobby_segments.txt", praatEXE,
#                                    50, 350,
#                                    forceRegenerate=True,
#                                    tgPath=wavPath,
#                                    tgFN="bobby_words.TextGrid",
#                                    tierName="word")

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
                                       "word", doPitch=True,
                                       medianFilterWindowSize=9)

pitch_and_intensity.generatePIMeasures(maryPitchData, tgPath,
                                       "mary.TextGrid",
                                       "word", doPitch=False,
                                       medianFilterWindowSize=9)

tg = tgio.openTextGrid(join(tgPath, "bobby_words.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "bobby_errors.TextGrid"))

tg = tgio.openTextGrid(join(tgPath, "mary.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "mary_errors.TextGrid"))

tg = tgio.openTextGrid(join(tgPath, "mary.TextGrid"))
tg = pitch_and_intensity.detectPitchErrors(maryFilteredPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "mary_filtered_errors.TextGrid"))

formantData = praat_scripts.getFormants(praatEXE,
                          join(wavPath, "bobby.wav"),
                          join(formantsPath, "bobby.txt"),
                          5500)
