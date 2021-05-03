"""
Code for reading, writing, and representing less complicated praat data files

see **examples/get_vowel_points.py**
"""

import io
from typing import List, Tuple, Optional, cast

from typing_extensions import Literal

from praatio.utilities import errors
from praatio.utilities import constants


class PointObject(object):
    def __init__(
        self,
        pointList: List[Tuple[float, ...]],
        objectClass: str,
        minTime: float = 0,
        maxTime: float = None,
    ):
        self.pointList = [tuple(row) for row in pointList]  # Sanitize input
        self.objectClass = objectClass
        self.minTime = minTime if minTime > 0 else 0
        self.maxTime = maxTime

    def __eq__(self, other):
        isEqual = True
        isEqual &= self.objectClass == other.objectClass
        isEqual &= self.minTime == other.minTime
        isEqual &= self.maxTime == other.maxTime
        isEqual &= len(self.pointList) == len(other.pointList)

        if isEqual:
            for selfEntry, otherEntry in zip(self.pointList, other.pointList):
                isEqual &= selfEntry == otherEntry

        return isEqual

    def save(self, fn: str) -> None:
        header = 'File type = "ooTextFile"\n' 'Object class = "%s"\n' "\n%s\n%s\n%d"
        header %= (
            self.objectClass,
            repr(self.minTime),
            repr(self.maxTime),
            len(self.pointList),
        )

        tmp = [repr(val) for entry in self.pointList for val in entry]
        strPoints = "\n".join(tmp)

        outputStr = u"%s\n%s\n" % (header, strPoints)

        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(outputStr)

    def getPointsInInterval(
        self, start: float, end: float, startIndex: int = 0
    ) -> List[float]:

        returnPointList = []
        for entry in self.pointList[startIndex:]:
            time = entry[0]
            if time >= start:
                if time <= end:
                    returnPointList.append(time)
                else:
                    break

        return returnPointList


class PointObject1D(PointObject):
    """Points that only carry temporal information"""

    def __init__(
        self,
        pointList: List[Tuple[float]],
        objectClass: Literal["point"],
        minTime: float = 0,
        maxTime: Optional[float] = None,
    ):

        suitable1dPointTypes = [constants.DataPointTypes.POINT]
        if objectClass not in suitable1dPointTypes:
            raise errors.WrongOption("objectClass", objectClass, suitable1dPointTypes)

        if maxTime is None:
            maxTime = max([row[0] for row in pointList])

        castPointList = cast(List[Tuple[float, ...]], pointList)
        super(PointObject1D, self).__init__(
            castPointList, objectClass, minTime, maxTime
        )


class PointObject2D(PointObject):
    """Points that carry a temporal value and some other value"""

    def __init__(
        self,
        pointList: List[Tuple[float, float]],
        objectClass: Literal["pitch", "duration"],
        minTime: float = 0,
        maxTime: float = None,
    ):
        suitable2dPointTypes = [
            constants.DataPointTypes.PITCH,
            constants.DataPointTypes.DURATION,
        ]
        if objectClass not in suitable2dPointTypes:
            raise errors.WrongOption(
                "objectClass",
                objectClass,
                suitable2dPointTypes,
            )

        if maxTime is None:
            maxTime = max([timeV for timeV, _ in pointList])

        castPointList = cast(List[Tuple[float, ...]], pointList)
        super(PointObject2D, self).__init__(
            castPointList, objectClass, minTime, maxTime
        )


def open1DPointObject(fn: str) -> PointObject1D:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index("=", start)
            except ValueError:
                break

            pointVal, start = _getNextValue(data, start)
            dataList.append((float(pointVal),))

        po = PointObject1D(dataList, objectType, minT, maxT)

    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataList = [(float(val),) for val in data.split("\n") if val.strip() != ""]
        po = PointObject1D(dataList, objectType, minT, maxT)

    return po


def open2DPointObject(fn: str) -> PointObject2D:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index("=", start)
            except ValueError:
                break

            timeVal, start = _getNextValue(data, start)

            try:
                start = data.index("=", start)
            except ValueError:
                break

            pointVal, start = _getNextValue(data, start)
            dataList.append(
                (
                    float(timeVal),
                    float(pointVal),
                )
            )

        po = PointObject2D(dataList, objectType, minT, maxT)

    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataStrList = data.split("\n")
        dataList = [
            (float(dataStrList[i]), float(dataStrList[i + 1]))
            for i in range(0, len(dataStrList), 2)
            if dataStrList[i].strip() != ""
        ]
        po = PointObject2D(dataList, objectType, minT, maxT)

    return po


def _parseNormalHeader(fn: str) -> Tuple[str, str, float, float]:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()

    chunkedData = data.split("\n", 7)

    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()

    data = chunkedData[-1]
    maxT = float(chunkedData[-4].split("=")[-1].strip())
    minT = float(chunkedData[-5].split("=")[-1].strip())

    return data, objectType, minT, maxT


def _getNextValue(data: str, start: int) -> Tuple[str, int]:
    end = data.index("\n", start)
    value = data[start + 1 : end]
    return value, end


def _parseShortHeader(fn: str) -> Tuple[str, str, float, float]:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()

    chunkedData = data.split("\n", 6)

    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()

    data = chunkedData[-1]
    maxT = float(chunkedData[-3])
    minT = float(chunkedData[-4])

    return data, objectType, minT, maxT
