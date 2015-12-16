'''
Created on Dec 16, 2014

@author: tmahrt

Extracts points in a PointProcess for the vowels specified in a textgrid
'''

import os
from os.path import join

from praatio import tgio
from praatio import dataio

path = join(".", "files")
outputPath = join(path, "point_process_output")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

tg = tgio.openTextGrid(join(path, "bobby_phones.TextGrid"))
pp = dataio.openPointProcess(join(path, "bobby.PointProcess"))

newPoints = []
tier = tg.tierDict["phone"]
for start, stop, label in tier.entryList:
    if label.lower()[0] not in ["a", "e", "i", "o", "u"]:
        continue
    newPoints.extend(pp.getPointsInInterval(start, stop))

outputPP = dataio.PointProcess(newPoints, pp.minTime, pp.maxTime)
outputPP.save(join(outputPath, "bobby_vowels.PointProcess"))
