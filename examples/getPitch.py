'''
Created on Jan 5, 2016

@author: tmahrt

Extracts pitch and intensity values in a wav file using praat
'''

import os
from os.path import join

from praatio import pitch_and_intensity
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


pitch_and_intensity.audioToPI(wavPath, "bobby.wav", pitchPath, "bobby.txt", 
                              praatEXE, 50, 350, forceRegenerate=False)

pitch_and_intensity.audioToPI(wavPath, "mary.wav", pitchPath, "mary.txt", 
                              praatEXE, 75, 450, forceRegenerate=False)

# Generate pitch and intensity values for all files
# (but only "mary.wav" has a ".TextGrid" file with the same name, so this
# will actually only generate data for one file)
pitch_and_intensity.getPIMeasuresBatch(pitchPath, tgPath, pitchMeasuresPath,
                                       "word",
                                       doPitch=True, outputSuffix="batch")

pitch_and_intensity.getPIMeasuresBatch(pitchPath, tgPath, rmsIntensityPath,
                                       "word",
                                       doPitch=False, outputSuffix="batch")

# Generate pitch and intensity values for one file
pitch_and_intensity.getPIMeasures(pitchPath, "bobby.txt", tgPath,
                                  "bobby_words.TextGrid", pitchMeasuresPath, 
                                  "word", doPitch=True, outputSuffix="")

pitch_and_intensity.getPIMeasures(pitchPath, "bobby.txt", tgPath,
                                  "bobby_words.TextGrid", rmsIntensityPath, 
                                  "word", doPitch=False, outputSuffix="")

