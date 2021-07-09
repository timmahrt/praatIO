"""
Praatio example for extracting points in a PointProcess for the vowels specified in a textgrid
"""

import os
from os.path import join

from praatio import textgrid
from praatio import data_points
from praatio.utilities import constants

path = join(".", "files")
outputPath = join(path, "point_process_output")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

tg = textgrid.openTextgrid(join(path, "bobby_phones.TextGrid"))
pp = data_points.open1DPointObject(join(path, "bobby.PointProcess"))

newPoints = []
tier = tg.tierDict["phone"]
for interval in tier.entryList:
    if interval.label.lower()[0] not in ["a", "e", "i", "o", "u"]:
        continue
    for val in pp.getPointsInInterval(interval.start, interval.end):
        newPoints.append((val,))

outputPP = data_points.PointObject1D(
    newPoints, constants.DataPointTypes.POINT, pp.minTime, pp.maxTime
)
outputPP.save(join(outputPath, "bobby_vowels.PointProcess"))
