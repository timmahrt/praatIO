"""
Various generic utility functions
"""

import os
from os.path import join
import subprocess
import functools
import itertools
import io
import wave
from pkg_resources import resource_filename
from typing import Any, Iterator, List, Tuple

from praatio.utilities import errors
from praatio.utilities import constants

# Get the folder one level above the current folder
scriptsPath = resource_filename(
    "praatio",
    "praatScripts",
)


def intervalOverlapCheck(
    interval: constants.Interval,
    cmprInterval: constants.Interval,
    percentThreshold: float = 0,
    timeThreshold: float = 0,
    boundaryInclusive: bool = False,
) -> bool:
    """
    Checks whether two intervals overlap

    Args:
        interval (Interval):
        cmprInterval (Interval):
        percentThreshold (float): if percentThreshold is greater than 0, then
            if the intervals overlap, they must overlap by at least this threshold
            (0.2 would mean 20% overlap considering both intervals)
            (eg [0, 6] and [3,8] have an overlap of 50%. If percentThreshold is set
             to higher than 50%, the intervals will be considered to not overlap.)
        timeThreshold (float): if greater than 0, then if the intervals overlap,
            they must overlap by at least this threshold
        boundaryInclusive (float): if true, then two intervals are considered to
            overlap if they share a boundary

    Returns:
        bool:
    """

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
    """
    Get the value in the data list (sorted by time) that occurs at this point

    If fuzzyMatching is True, if there is not a value
    at the requested timestamp, the nearest feature value will be taken.

    The procedure assumes that all data is ordered in time.
    dataTupleList should be in the form
    [(t1, v1a, v1b, ..), (t2, v2a, v2b, ..), ..]

    The procedure makes one pass through dataTupleList and one
    pass through self.entryList.  If the data is not sequentially
    ordered, the incorrect response will be returned.

    For efficiency purposes, it takes a starting index and returns the ending
    index.
    """

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
    """
    Gets the values that exist within an interval

    The function assumes that the data is formated as
    [(t1, v1a, v1b, ...), (t2, v2a, v2b, ...)]
    """

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
    inputList: List[Tuple[float, float]], maxValue: float = None
) -> List[Tuple[float, float]]:
    """
    Inverts the segments of a list of intervals

    e.g.
    [(0,1), (4,5), (7,10)] -> [(1,4), (5,7)]
    [(0.5, 1.2), (3.4, 5.0)] -> [(0.0, 0.5), (1.2, 3.4)]
    """
    inputList = sorted(inputList)

    # Special case -- empty lists
    invList: List[Tuple[float, float]]
    if len(inputList) == 0 and maxValue is not None:
        invList = [
            (0, maxValue),
        ]
    else:
        # Insert in a garbage head and tail value for the purpose
        # of inverting, in the range does not start and end at the
        # smallest and largest values
        if inputList[0][0] != 0:
            inputList.insert(0, (-1, 0))
        if maxValue is not None and inputList[-1][1] < maxValue:
            inputList.append((maxValue, maxValue + 1))

        invList = [
            (inputList[i][1], inputList[i + 1][0]) for i in range(0, len(inputList) - 1)
        ]

    return invList


def makeDir(path: str) -> None:
    """
    Creates a new directory

    Unlike os.mkdir, it does not throw an exception if the directory already exists.
    """
    if not os.path.exists(path):
        os.mkdir(path)


def findAll(txt: str, subStr: str) -> List[int]:
    """
    Find the starting indicies of all instances of subStr in txt
    """
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


def _getMatchFunc(pattern: str):
    """
    An unsophisticated pattern matching function
    """

    # '#' Marks word boundaries, so if there is more than one we need to do
    #    something special to make sure we're not mis-representings them
    assert pattern.count("#") < 2

    def startsWith(subStr, fullStr):
        return fullStr[: len(subStr)] == subStr

    def endsWith(subStr, fullStr):
        return fullStr[-1 * len(subStr) :] == subStr

    def inStr(subStr, fullStr):
        return subStr in fullStr

    # Selection of the correct function
    if pattern[0] == "#":
        pattern = pattern[1:]
        cmpFunc = startsWith

    elif pattern[-1] == "#":
        pattern = pattern[:-1]
        cmpFunc = endsWith

    else:
        cmpFunc = inStr

    return functools.partial(cmpFunc, pattern)


def findFiles(
    path: str,
    filterPaths: bool = False,
    filterExt: str = None,
    filterPattern: str = None,
    skipIfNameInList: List[str] = None,
    stripExt: bool = False,
) -> List[str]:

    fnList = os.listdir(path)

    if filterPaths is True:
        fnList = [
            folderName
            for folderName in fnList
            if os.path.isdir(os.path.join(path, folderName))
        ]

    if filterExt is not None:
        splitFNList = [[fn, *list(os.path.splitext(fn))] for fn in fnList]
        fnList = [fn for fn, name, ext in splitFNList if ext == filterExt]

    if filterPattern is not None:
        splitFNList = [[fn, *list(os.path.splitext(fn))] for fn in fnList]
        matchFunc = _getMatchFunc(filterPattern)
        fnList = [fn for fn, name, ext in splitFNList if matchFunc(name)]

    if skipIfNameInList is not None:
        targetNameList = [os.path.splitext(fn)[0] for fn in skipIfNameInList]
        fnList = [fn for fn in fnList if os.path.splitext(fn)[0] not in targetNameList]

    if stripExt is True:
        fnList = [os.path.splitext(fn)[0] for fn in fnList]

    fnList.sort()
    return fnList


def openCSV(path: str, fn: str, encoding: str = "utf-8") -> List[List[str]]:
    """
    Load a feature

    In many cases we only want a single value from the feature (mainly because
    the feature only contains one value).  In these situations, the user
    can indicate that rather than receiving a list of lists, they can receive
    a lists of values, where each value represents the item in the row
    indicated by valueIndex.
    """

    # Load CSV file
    with io.open(join(path, fn), "r", encoding=encoding) as fd:
        featureList = fd.read().splitlines()
    return [rowStr.split(",") for rowStr in featureList]


def getRowFromCSV(
    path: str, fn: str, valueIndex: int, encoding: str = "utf-8"
) -> List[str]:
    featureListOfLists = openCSV(path, fn, encoding)

    return [row[valueIndex] for row in featureListOfLists]


def safeZip(listOfLists: List[list], enforceLength: bool) -> Iterator[Any]:
    """
    A safe version of python's zip()

    If two sublists are of different sizes, python's zip will truncate
    the output to be the smaller of the two.

    safeZip throws an exception if the size of the any sublist is different
    from the rest.
    """
    if enforceLength is True:
        length = len(listOfLists[0])
        assert all([length == len(subList) for subList in listOfLists])

    return itertools.zip_longest(*listOfLists)


def getWavDuration(wavFN: str) -> float:
    "For internal use.  See praatio.audio.WavQueryObj() for general use."
    audiofile = wave.open(wavFN, "r")
    params = audiofile.getparams()
    framerate = params[2]
    nframes = params[3]
    duration = float(nframes) / framerate

    return duration
