'''
Created on Nov 9, 2015

@author: tmahrt
'''

import os
from os.path import join

from praatio import kgio

path = os.path.abspath(join(".", "files"))
outputPath = join(path, "resynthesized_wavs")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

# File to manipulate
name = "bobby"
wavFN = join(path, name + ".wav")
mainKlaatFN = join(outputPath, name + ".KlattGrid")

# Wav to klaatgrid
praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"
kgio.wavToKlaatGrid(praatEXE, wavFN, mainKlaatFN, maxFormantFreq=3500,
                    pitchFloor=50, pitchCeiling=350)

# Increase formants by 20%
incrTwenty = lambda x: x * 1.2

kg = kgio.openKlattGrid(mainKlaatFN)

formantTier = kg.tierDict["oral_formants"]
subFormantTier = formantTier.tierDict["formants"]
for subTierName in subFormantTier.tierNameList:
    subFormantTier.tierDict[subTierName].modifyValues(incrTwenty)

kg.save(join(outputPath, name + "_twenty_percent_more.KlattGrid"))


# Decrease formants by 20% - same technique as above, but shorthand version
# (also less flexible)
decrTwenty = lambda x: x * 0.8
kg = kgio.openKlattGrid(mainKlaatFN)
kg.tierDict["oral_formants"].modifySubtiers("formants",decrTwenty)
kg.save(join(outputPath, name + "_twenty_percent_less.KlattGrid"))

