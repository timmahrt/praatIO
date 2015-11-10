'''
Created on Nov 9, 2015

@author: tmahrt
'''

import os
from os.path import join

from praatio import kgio

path = join(".", "files")
outputPath = join(path, "resynthesized_wavs")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)


# Increase formants by 20%
incrTwenty = lambda x: x * 1.2

kg = kgio.openKlattGrid(join(path, "bobby.KlattGrid"))

formantTier = kg.tierDict["oral_formants"]
subFormantTier = formantTier.tierDict["formants"]
for subTierName in subFormantTier.tierNameList:
    subFormantTier.tierDict[subTierName].modifyValues(incrTwenty)

kg.save(join(outputPath, "bobby_twenty_percent_more.KlattGrid"))


# Decrease formants by 20% - same technique as above, but shorthand version
# (also less flexible)
decrTwenty = lambda x: x * 0.8
kg = kgio.openKlattGrid(join(path, "bobby.KlattGrid"))
kg.tierDict["oral_formants"].modifySubtiers("formants",decrTwenty)
kg.save(join(outputPath, "bobby_twenty_percent_less.KlattGrid"))

