"""
Praatio example for extracting points in a PointProcess for the vowels specified in a textgrid
"""

import os
from os.path import join

from praatio import textgrid
from praatio import dataio

path = join(".", "files")
outputPath = join(path, "point_process_output")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

tg = textgrid.openTextgrid(join(path, "bobby_phones.TextGrid"))
pp = dataio.open1DPointObject(join(path, "bobby.PointProcess"))

newPoints = []
tier = tg.tierDict["phone"]
for start, stop, label in tier.entryList:
    if label.lower()[0] not in ["a", "e", "i", "o", "u"]:
        continue
    newPoints.extend(
        [
            pp.getPointsInInterval(start, stop),
        ]
    )

outputPP = dataio.PointObject1D(newPoints, dataio.POINT, pp.minTime, pp.maxTime)
outputPP.save(join(outputPath, "bobby_vowels.PointProcess"))
