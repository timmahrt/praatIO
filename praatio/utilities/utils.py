"""
Various generic utility functions
"""

import os
import subprocess
import itertools
import wave
from pkg_resources import resource_filename
from typing_extensions import Literal
from typing import Any, Iterator, List, Tuple, NoReturn, Type, Optional

from praatio.utilities import errors
from praatio.utilities import constants

Interval = constants.Interval

# Get the folder one level above the current folder
scriptsPath = resource_filename(
    "praatio",
    "praatScripts",
)


def find(list, value, reverse) -> Optional[int]:
    """Returns the first/last index of an item in a list"""
    if value not in list:
        return None

    if reverse:
        index = len(list) - list[::-1].index(value) - 1
    else:
        index = list.index(value)

    return index


def reportNoop(_exception: Type[BaseException], _text: str) -> None:
    pass


def reportException(exception: Type[BaseException], text: str) -> NoReturn:
    raise exception(text)


def reportWarning(_exception: Type[BaseException], text: str) -> None:
    print(text)


def getErrorReporter(reportingMode: Literal["silence", "warning", "error"]):
    modeToFunc = {
        constants.ErrorReportingMode.SILENCE: reportNoop,
        constants.ErrorReportingMode.WARNING: reportWarning,
        constants.ErrorReportingMode.ERROR: reportException,
    }

    return modeToFunc[reportingMode]


def checkIsUndershoot(time: float, referenceTime: float, errorReporter) -> bool:
    if time < referenceTime:
        errorReporter(
            errors.OutOfBounds,
            f"'{time}' occurs before minimum allowed time '{referenceTime}'",
        )
        return True
    else:
        return False


def checkIsOvershoot(time: float, referenceTime: float, errorReporter) -> bool:
    if time > referenceTime:
        errorReporter(
            errors.OutOfBounds,
            f"'{time}' occurs after maximum allowed time '{referenceTime}'",
        )
        return True
    else:
        return False


def validateOption(variableName, value, optionClass):
    if value not in optionClass.validOptions:
        raise errors.WrongOption(variableName, value, optionClass.validOptions)


def intervalOverlapCheck(
    interval: Interval,
    cmprInterval: Interval,
    percentThreshold: float = 0,
    timeThreshold: float = 0,
    boundaryInclusive: bool = False,
) -> bool:
    """Checks whether two intervals overlap

    Args:
        interval:
        cmprInterval:
        percentThreshold: if percentThreshold is greater than 0, then
            if the intervals overlap, they must overlap by at least this threshold
            (0.2 would mean 20% overlap considering both intervals)
            (eg [0, 6] and [3,8] have an overlap of 50%. If percentThreshold is set
             to higher than 50%, the intervals will be considered to not overlap.)
        timeThreshold: if greater than 0, then if the intervals overlap,
            they must overlap by at least this threshold
        boundaryInclusive: if true, then two intervals are considered to
            overlap if they share a boundary

    Returns:
        bool:
    """
    # TODO: move to Interval class?
    startTime, endTime = interval[:2]
    cmprStartTime, cmprEndTime = cmprInterval[:2]

    overlapTime = max(0, min(endTime, cmprEndTime) - max(startTime, cmprStartTime))
    overlapFlag = overlapTime > 0

    # Do they share a boundary?  Only need to check if one boundary ends
    # when another begins (because otherwise, they overlap in other ways)
    boundaryOverlapFlag = False
    if boundaryInclusive:
        boundaryOverlapFlag = startTime == cmprEndTime or endTime == cmprStartTime

    # Is the overlap over a certain percent?
    percentOverlapFlag = False
    if percentThreshold > 0 and overlapFlag:
        totalTime = max(endTime, cmprEndTime) - min(startTime, cmprStartTime)
        percentOverlap = overlapTime / float(totalTime)

        percentOverlapFlag = percentOverlap >= percentThreshold
        overlapFlag = percentOverlapFlag

    # Is the overlap more than a certain threshold?
    timeOverlapFlag = False
    if timeThreshold > 0 and overlapFlag:
        timeOverlapFlag = overlapTime >= timeThreshold
        overlapFlag = timeOverlapFlag

    overlapFlag = (
        overlapFlag or boundaryOverlapFlag or percentOverlapFlag or timeOverlapFlag
    )

    return overlapFlag


def getIntervalsInInterval(
    start: float,
    end: float,
    intervals: List[Interval],
    mode: Literal["strict", "lax", "truncated"],
) -> List[Interval]:
    """Gets all intervals that exist between /start/ and /end/

    Args:
        start: the target interval start time
        end: the target interval stop time
        intervals: the list of intervals to check
        mode: Determines judgement criteria
            - 'strict', only intervals wholly contained by the target
                interval will be kept
            - 'lax', partially contained intervals will be kept
            - 'truncated', partially contained intervals will be
                truncated to fit within the crop region.

    Returns:
        The list of intervals that overlap with the target interval
    """
    # TODO: move to Interval class?
    validateOption("mode", mode, constants.CropCollision)

    containedIntervals = []
    for interval in intervals:
        matchedEntry = None

        # Don't need to investigate if the current interval is
        # before start or after end
        if interval.end <= start or interval.start >= end:
            continue

        # Determine if the current interval is wholly contained
        # within the superEntry
        if interval.start >= start and interval.end <= end:
            matchedEntry = interval

        # If the current interval is only partially contained within the
        # target interval AND inclusion is 'lax', include it anyways
        elif mode == constants.CropCollision.LAX and (
            interval.start >= start or interval.end <= end
        ):
            matchedEntry = interval

        # The current interval stradles the end of the target interval
        elif interval.start >= start and interval.end > end:
            if mode == constants.CropCollision.TRUNCATED:
                matchedEntry = Interval(interval.start, end, interval.label)

        # The current interval stradles the start of the target interval
        elif interval.start < start and interval.end <= end:
            if mode == constants.CropCollision.TRUNCATED:
                matchedEntry = Interval(start, interval.end, interval.label)

        # The current interval contains the target interval completely
        elif interval.start <= start and interval.end >= end:
            if mode == constants.CropCollision.LAX:
                matchedEntry = interval
            elif mode == constants.CropCollision.TRUNCATED:
                matchedEntry = Interval(start, end, interval.label)

        if matchedEntry is not None:
            containedIntervals.append(matchedEntry)

    return containedIntervals


def escapeQuotes(text: str) -> str:
    return text.replace('"', '""')


def strToIntOrFloat(inputStr: str) -> float:
    return float(inputStr) if "." in inputStr else int(inputStr)


def getValueAtTime(
    timestamp: float,
    sortedDataTupleList: List[Tuple[Any, ...]],
    fuzzyMatching: bool = False,
    startI: int = 0,
) -> Tuple[Tuple[Any, ...], int]:
    """Get the value in the data list (sorted by time) that occurs at this point

    If fuzzyMatching is True, if there is not a value
    at the requested timestamp, the nearest feature value will be taken.

    The procedure assumes that all data is ordered in time.
    dataTupleList should be in the form
    [(t1, v1a, v1b, ..), (t2, v2a, v2b, ..), ..]

    The procedure makes one pass through dataTupleList and one
    pass through self.entries.  If the data is not sequentially
    ordered, the incorrect response will be returned.

    For efficiency purposes, it takes a starting index and returns the ending
    index.
    """
    # TODO: move to Point class?
    i = startI
    bestRow: Tuple[Any, ...] = ()

    # Only find exact timestamp matches
    if fuzzyMatching is False:
        while True:
            try:
                currRow = sortedDataTupleList[i]
            except IndexError:
                break

            currTime = currRow[0]
            if currTime >= timestamp:
                if timestamp == currTime:
                    bestRow = currRow
                break
            i += 1

    # Find the closest timestamp
    else:
        bestTime = sortedDataTupleList[i][0]
        bestRow = sortedDataTupleList[i]
        while True:
            try:
                dataTuple = sortedDataTupleList[i]
            except IndexError:
                i -= 1
                break  # Last known value is the closest one

            currTime = dataTuple[0]
            currRow = dataTuple

            currDiff = abs(currTime - timestamp)
            bestDiff = abs(bestTime - timestamp)
            if currDiff < bestDiff:  # We're closer to the target val
                bestTime = currTime
                bestRow = currRow
                if currDiff == 0:
                    break  # Can't do better than a perfect match
            elif currDiff > bestDiff:
                i -= 1
                break  # We've past the best value.
            i += 1

    retRow = bestRow

    return retRow, i


def getValuesInInterval(dataTupleList: List, start: float, end: float) -> List:
    """Gets the values that exist within an interval

    The function assumes that the data is formated as
    [(t1, v1a, v1b, ...), (t2, v2a, v2b, ...)]
    """
    # TODO: move to Interval class?
    intervalDataList = []
    for dataTuple in dataTupleList:
        time = dataTuple[0]
        if start <= time and end >= time:
            intervalDataList.append(dataTuple)

    return intervalDataList


def sign(x: float) -> int:
    """Returns 1 if x is positive, 0 if x is 0, and -1 otherwise"""
    retVal = 0
    if x > 0:
        retVal = 1
    elif x < 0:
        retVal = -1
    return retVal


def invertIntervalList(
    inputList: List[Tuple[float, float]], minValue: float = None, maxValue: float = None
) -> List[Tuple[float, float]]:
    """Inverts the segments of a list of intervals

    e.g.
    [(0,1), (4,5), (7,10)] -> [(1,4), (5,7)]
    [(0.5, 1.2), (3.4, 5.0)] -> [(0.0, 0.5), (1.2, 3.4)]
    """
    if any([interval[0] >= interval[1] for interval in inputList]):
        raise errors.ArgumentError("Interval start occured before interval end")

    inputList = sorted(inputList)

    # Special case -- empty lists
    invList: List[Tuple[float, float]]
    if len(inputList) == 0 and minValue is not None and maxValue is not None:
        invList = [
            (minValue, maxValue),
        ]
    else:
        # Insert in a garbage head and tail value for the purpose
        # of inverting, in the range does not start and end at the
        # smallest and largest values
        if minValue is not None and inputList[0][0] > minValue:
            inputList.insert(0, (-1, minValue))
        if maxValue is not None and inputList[-1][1] < maxValue:
            inputList.append((maxValue, maxValue + 1))

        invList = [
            (inputList[i][1], inputList[i + 1][0]) for i in range(0, len(inputList) - 1)
        ]

        # If two intervals in the input share a boundary, we'll get invalid intervals in the output
        # eg invertIntervalList([(0, 1), (1, 2)]) -> [(1, 1)]
        invList = [interval for interval in invList if interval[0] != interval[1]]

    return invList


def makeDir(path: str) -> None:
    """Create a new directory

    Unlike os.mkdir, it does not throw an exception if the directory already exists
    """
    if not os.path.exists(path):
        os.mkdir(path)


def findAll(txt: str, subStr: str) -> List[int]:
    """Find the starting indicies of all instances of subStr in txt"""
    indexList = []
    index = 0
    while True:
        try:
            index = txt.index(subStr, index)
        except ValueError:
            break
        indexList.append(int(index))
        index += 1

    return indexList


def runPraatScript(
    praatEXE: str, scriptFN: str, argList: List[Any], cwd: str = None
) -> None:

    # Popen gives a not-very-transparent error
    if not os.path.exists(praatEXE):
        raise errors.FileNotFound(praatEXE)
    if not os.path.exists(scriptFN):
        raise errors.FileNotFound(scriptFN)

    argList = ["%s" % arg for arg in argList]
    cmdList = [praatEXE, "--run", scriptFN] + argList

    myProcess = subprocess.Popen(cmdList, cwd=cwd)

    if myProcess.wait():
        raise errors.PraatExecutionFailed(cmdList)


def safeZip(listOfLists: List[list], enforceLength: bool) -> Iterator[Any]:
    """A safe version of python's zip()

    If two sublists are of different sizes, python's zip will truncate
    the output to be the smaller of the two.

    safeZip throws an exception if the size of the any sublist is different
    from the rest.
    """
    if enforceLength is True:
        length = len(listOfLists[0])
        if not all([length == len(subList) for subList in listOfLists]):
            raise errors.SafeZipException("Lists to zip have different sizes.")

    return itertools.zip_longest(*listOfLists)


def getWavDuration(wavFN: str) -> float:
    "For internal use.  See praatio.audio.QueryWav() for general use."
    audiofile = wave.open(wavFN, "r")
    params = audiofile.getparams()
    framerate = params[2]
    nframes = params[3]
    duration = float(nframes) / framerate

    return duration


def chooseClosestTime(
    targetTime: float, candidateA: Optional[float], candidateB: Optional[float]
) -> float:
    """Chooses the closest time between two options that straddle the target time

    Args:
        targetTime: the time to compare against
        candidateA: the first candidate
        candidateB: the second candidate

    Returns:
        the closer of the two options to the target time
    Raises:
        ArgumentError: When no left or right candidate is provided
    """
    closestTime: float
    if candidateA is None and candidateB is None:
        raise (errors.ArgumentError("Must provide at"))

    elif candidateA is None and candidateB is not None:
        closestTime = candidateB
    elif candidateB is None and candidateA is not None:
        closestTime = candidateA
    elif candidateB is not None and candidateA is not None:
        aDiff = abs(candidateA - targetTime)
        bDiff = abs(candidateB - targetTime)

        if aDiff <= bDiff:
            closestTime = candidateA
        else:
            closestTime = candidateB

    return closestTime


def getInterval(
    startTime: float, duration: float, max: float, reverse: bool
) -> Tuple[float, float]:
    """returns an interval before or after some start time

    The returned timestamps will be between 0 and max

    Args:
        startTime: the time to get the interval from
        duration: duration of the interval
        max: the maximum allowed time
        reverse: is the interval before or after the targetTime?

    Returns:
        the start and end time of an interval
    """
    if reverse is True:
        endTime = startTime
        startTime -= duration
    else:
        endTime = startTime + duration

    # Don't read over the edges
    if startTime < 0:
        startTime = 0
    elif endTime > max:
        endTime = max

    return (startTime, endTime)
