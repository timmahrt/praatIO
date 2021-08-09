"""
Various math utilities
"""

import math
import statistics
from typing import Callable, List, Tuple

from praatio.utilities import errors


def numToStr(inputNum: float) -> str:
    if isclose(inputNum, int(inputNum)):
        retVal = "%d" % inputNum
    else:
        retVal = "%s" % repr(inputNum)
    return retVal


def isclose(a: float, b: float, rel_tol: float = 1e-14, abs_tol: float = 0.0) -> bool:
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def filterTimeSeriesData(
    filterFunc: Callable[[List[float], int, bool], List[float]],
    featureTimeList: List[list],
    windowSize: int,
    index: int,
    useEdgePadding: bool,
) -> List[list]:
    """
    Filter time-stamped data values within a window

    filterFunc could be medianFilter() or znormFilter()

    It's ok to have other values in the list. eg
    featureTimeList: [(time_0, .., featureA_0, ..),
                      (time_1, .., featureA_1, ..),
                      ..]
    """
    featureTimeList = [list(row) for row in featureTimeList]
    featValues = [row[index] for row in featureTimeList]
    featValues = filterFunc(featValues, windowSize, useEdgePadding)

    if len(featureTimeList) != len(featValues):
        errors.ArgumentError(
            "The length of the time values {len(featureTimeList)} does not "
            "match the length of the data values {len(featValues)}"
        )
    outputList = [
        [*piRow[:index], f0Val, *piRow[index + 1 :]]
        for piRow, f0Val in zip(featureTimeList, featValues)
    ]

    return outputList


def znormalizeSpeakerData(
    featureTimeList: List[Tuple[float, ...]], index: int, filterZeroValues: bool
) -> List[Tuple[float, ...]]:
    """
    znormalize time series data

    The idea is to normalize each speaker separately to be able
    to compare data across several speakers for speaker-dependent
    data like pitch range

    To normalize a speakers data within a local window, use filterTimeSeriesData()

    filterZeroValues: if True, don't consider zero values in the mean and stdDev
      (recommended value for data like pitch or intensity)
    """
    featValues = [row[index] for row in featureTimeList]

    if not filterZeroValues:
        featValues = znormalizeData(featValues)
    else:
        featValuesNoZeroes = [val for val in featValues if val != ""]
        meanVal = statistics.mean(featValuesNoZeroes)
        stdDevVal = statistics.stdev(featValuesNoZeroes)

        featValues = [
            (val - meanVal) / stdDevVal if val > 0 else 0 for val in featValues
        ]

    if len(featureTimeList) != len(featValues):
        errors.ArgumentError(
            "The length of the time values {len(featureTimeList)} does not "
            "match the length of the data values {len(featValues)}"
        )
    outputList = [
        tuple([*piRow[:index], val, *piRow[index + 1 :]])
        for piRow, val in zip(featureTimeList, featValues)
    ]

    return outputList


def medianFilter(dist: List[float], window: int, useEdgePadding: bool) -> List[float]:
    """
    median filter each value in a dataset; filtering occurs within a given window

    Median filtering is used to "smooth" out extreme values.  It can be useful if
    your data has lots of quick spikes.  The larger the window, the flatter the output
    becomes.
    Given:
    x = [1 1 1 9 5 2 4 7 4 5 1 5]
    medianFilter(x, 5, False)
    >> [1 1 1 2 4 5 4 4 4 5 1 5]
    """
    return _stepFilter(statistics.median, dist, window, useEdgePadding)


def znormWindowFilter(
    dist: List[float], window: int, useEdgePadding: bool, filterZeroValues: bool
) -> List[float]:
    """
    z-normalize each value in a dataset; normalization occurs within a given window

    If you suspect that events are sensitive to local changes, (e.g. local changes in pitch
    are more important absolute differences in pitch) then using windowed
    znormalization is appropriate.

    See znormalizeData() for more information on znormalization.
    """

    def znormalizeCenterVal(valList):
        valToNorm = valList[int(len(valList) / 2.0)]
        return (valToNorm - statistics.mean(valList)) / statistics.stdev(valList)

    if not filterZeroValues:
        filteredOutput = _stepFilter(znormalizeCenterVal, dist, window, useEdgePadding)
    else:
        zeroIndexList = []
        nonzeroValList = []
        for i, val in enumerate(dist):
            if val > 0.0:
                nonzeroValList.append(val)
            else:
                zeroIndexList.append(i)

        filteredOutput = _stepFilter(
            znormalizeCenterVal, nonzeroValList, window, useEdgePadding
        )

        for i in zeroIndexList:
            filteredOutput.insert(i, 0.0)

    return filteredOutput


def _stepFilter(
    filterFunc, dist: List[float], window: int, useEdgePadding: bool
) -> List[float]:

    offset = int(math.floor(window / 2.0))
    length = len(dist)

    returnList = []
    for x in range(length):
        dataToFilter = []
        # If using edge padding or if 0 <= context <= length
        if useEdgePadding or (((0 <= x - offset) and (x + offset < length))):

            preContext: List[float] = []
            currentContext = [
                dist[x],
            ]
            postContext = []

            lastKnownLargeIndex = 0
            for y in range(1, offset + 1):  # 1-based
                if x + y >= length:
                    if lastKnownLargeIndex == 0:
                        largeIndexValue = x
                    else:
                        largeIndexValue = lastKnownLargeIndex
                else:
                    largeIndexValue = x + y
                    lastKnownLargeIndex = x + y

                postContext.append(dist[largeIndexValue])

                if x - y < 0:
                    smallIndexValue = 0
                else:
                    smallIndexValue = x - y

                preContext.insert(0, dist[smallIndexValue])

            dataToFilter = preContext + currentContext + postContext
            value = filterFunc(dataToFilter)
        else:
            value = dist[x]
        returnList.append(value)

    return returnList


def znormalizeData(valList: List[float]) -> List[float]:
    """
    Given a list of floats, return the z-normalized values of the floats

    The formula is: z(v) = (v - mean) / stdDev
    In effect, this scales all values to the range [-4, 4].
    It can be used, for example, to compare the pitch values of different speakers who
    naturally have different pitch ranges.
    """
    valList = valList[:]
    meanVal = statistics.mean(valList)
    stdDevVal = statistics.stdev(valList)

    return [(val - meanVal) / stdDevVal for val in valList]


def rms(intensityValues: List[float]) -> float:
    """Return the root mean square for the input set of values"""
    intensityValues = [val ** 2 for val in intensityValues]
    meanVal = sum(intensityValues) / len(intensityValues)
    return math.sqrt(meanVal)
