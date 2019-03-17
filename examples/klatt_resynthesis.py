'''
Created on Nov 9, 2015

@author: tmahrt
'''

import os
from os.path import join

from praatio import kgio
from praatio import praat_scripts

path = os.path.abspath(join(".", "files"))
outputPath = join(path, "resynthesized_wavs")
if not os.path.exists(outputPath):
    os.mkdir(outputPath)

# File to manipulate
name = "bobby"
wavFN = join(path, name + ".wav")
mainKlaatFN = join(outputPath, name + ".KlattGrid")

# Wav to klaatgrid
praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"  # Example for Mac
# praatEXE = r"C:\Praat.exe" # Example for Windows
kgio.wavToKlattgrid(praatEXE, wavFN, mainKlaatFN, maxFormantFreq=3500,
                    pitchFloor=50, pitchCeiling=350)

# Increase formants by 20%
incrTwenty = lambda x: x * 1.2
kg = kgio.openKlattgrid(mainKlaatFN)

formantTier = kg.tierDict["oral_formants"]
subFormantTier = formantTier.tierDict["formants"]
for subTierName in subFormantTier.tierNameList:
    subFormantTier.tierDict[subTierName].modifyValues(incrTwenty)

outputName = name + "_twenty_percent_more"
klattFN = join(outputPath, outputName + ".KlattGrid")
outputWavFN = join(outputPath, outputName + ".wav")
kg.save(klattFN)
kgio.resynthesize(praatEXE, wavFN, klattFN, outputWavFN)

# Decrease formants by 20% - same technique as above, but shorthand version
# (also less flexible)
decrTwenty = lambda x: x * 0.8
kg = kgio.openKlattgrid(mainKlaatFN)
kg.tierDict["oral_formants"].modifySubtiers("formants", decrTwenty)

outputName = name + "_twenty_percent_less"
klattFN = join(outputPath, outputName + ".KlattGrid")
outputWavFN = join(outputPath, outputName + ".wav")
kg.save(klattFN)
kgio.resynthesize(praatEXE, wavFN, klattFN, outputWavFN)

# Decrease formants by 20% using praat's changeGender function
outputWavFN = join(outputPath, outputName + "_changeGender.wav")
praat_scripts.changeGender(praatEXE, wavFN, outputWavFN, 75, 600, 0.8)
