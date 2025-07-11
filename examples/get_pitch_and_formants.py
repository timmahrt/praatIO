"""
Praatio example for extracting pitch and intensity values in a wav file using praat.
"""

import os
from os.path import join

from praatio import pitch_and_intensity
from praatio import praat_scripts
from praatio import textgrid
from praatio.utilities import utils

wavPath = os.path.abspath(join(".", "files"))
tgPath = os.path.abspath(join(".", "files"))
rootOutputFolder = os.path.abspath(join(".", "files", "pitch_extraction"))
pitchPath = join(rootOutputFolder, "pitch")
formantsPath = join(rootOutputFolder, "formants")
pitchMeasuresPath = join(rootOutputFolder, "pitch_measures")
rmsIntensityPath = join(rootOutputFolder, "rms_intensity")


praatEXE = r"C:\Praat.exe"
# praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"
utils.makeDir(rootOutputFolder)
utils.makeDir(pitchPath)
utils.makeDir(pitchMeasuresPath)
utils.makeDir(rmsIntensityPath)
utils.makeDir(formantsPath)

bobbyPitchData = pitch_and_intensity.extractPI(
    join(wavPath, "bobby.wav"),
    join(pitchPath, "bobby.txt"),
    praatEXE,
    50,
    350,
    forceRegenerate=False,
)

# Here are two examples of the new functionality of extracting pitch
# from only labeled intervals in a textgrid.

# Extracts each labeled interval as a separate wave file, extracts the
# pitch track from each of those, and then aggregates the result.
pitch_and_intensity.extractPI(
    join(wavPath, "bobby.wav"),
    join(pitchPath, "bobby_segments.txt"),
    praatEXE,
    50,
    350,
    forceRegenerate=True,
    tgFN=join(wavPath, "bobby_words.TextGrid"),
    tierName="phrase",
)

# Generates the entire pitch contour for the file, but only saves the
# labeled sections.  Functionally the same as the commented-out code above.
# pitch_and_intensity._extractPIFile(join(wavPath, "bobby.wav"),
#                                    join(pitchPath, "bobby_segments.txt"),
#                                    praatEXE, 50, 350,
#                                    forceRegenerate=True,
#                                    tgFN=join(wavPath, "bobby_words.TextGrid"),
#                                    tierName="word")


# If you have short intervals (word length or shorter) you will probably get errors
# from praat with the above code.  The sampling window has to be a certain size to
# get good results.  You might have better luck getting the pitch over the entire
# file and then filtering only the pitch values that fall inside your labeled intervals
maryPitchData = pitch_and_intensity.extractPI(
    join(wavPath, "mary.wav"),
    join(pitchPath, "mary.txt"),
    praatEXE,
    75,
    450,
    forceRegenerate=False,
)
tg = textgrid.openTextgrid(join(tgPath, "mary.TextGrid"), False)
tier = tg.getTier("phone")
filteredData = tier.getValuesInIntervals(maryPitchData)

maryPitchData = pitch_and_intensity.extractPI(
    join(wavPath, "mary.wav"),
    join(pitchPath, "mary.txt"),
    praatEXE,
    75,
    450,
    forceRegenerate=False,
)

maryPitchData = pitch_and_intensity.extractPI(
    join(wavPath, "mary.wav"),
    join(pitchPath, "mary_interpolated.txt"),
    praatEXE,
    75,
    450,
    forceRegenerate=False,
    pitchQuadInterp=True,
)


filteredFN = "mary_300hz_high_pass_filtered.wav"
maryFilteredPitchData = pitch_and_intensity.extractPitch(
    join(wavPath, filteredFN),
    join(pitchPath, "mary_filtered.txt"),
    praatEXE,
    75,
    450,
    forceRegenerate=False,
)

# Generate pitch and intensity values for one file
pitch_and_intensity.generatePIMeasures(
    bobbyPitchData,
    join(tgPath, "bobby_words.TextGrid"),
    "word",
    doPitch=True,
    medianFilterWindowSize=9,
)

pitch_and_intensity.generatePIMeasures(
    maryPitchData,
    join(tgPath, "mary.TextGrid"),
    "word",
    doPitch=False,
    medianFilterWindowSize=9,
)

tg = textgrid.openTextgrid(join(tgPath, "bobby_words.TextGrid"), False)
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "bobby_errors.TextGrid"), "short_textgrid", True)

tg = textgrid.openTextgrid(join(tgPath, "mary.TextGrid"), False)
tg = pitch_and_intensity.detectPitchErrors(bobbyPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "mary_errors.TextGrid"), "short_textgrid", True)

tg = textgrid.openTextgrid(join(tgPath, "mary.TextGrid"), False)
tg = pitch_and_intensity.detectPitchErrors(maryFilteredPitchData, 0.75, tg)[1]
tg.save(join(rootOutputFolder, "mary_filtered_errors.TextGrid"), "short_textgrid", True)

formantData = praat_scripts.getFormants(
    praatEXE, join(wavPath, "bobby.wav"), join(formantsPath, "bobby.txt"), 5500
)
