"""
An PointObject is used for storing non-annotation data in praat

There are two variants: PointObject1D and PointObject2D

PointObject1D only stores temporal data (it can track pulses/occurances in time).
PointObject2D stores temporal data and some other data (eg pitch).  It's not
so different from a PointTier, except that PointTiers specifically hold annotation
data.
"""
import io

from typing_extensions import Literal
from typing import List, Optional, Tuple, cast

from praatio.utilities import constants
from praatio.utilities import errors


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
