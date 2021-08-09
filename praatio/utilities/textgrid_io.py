import re
import json
from typing import Optional, Tuple, List, Any, Dict, Match

from typing_extensions import Literal

from praatio.utilities import errors
from praatio.utilities import my_math
from praatio.utilities import utils
from praatio.utilities.constants import (
    TextgridFormats,
    MIN_INTERVAL_LENGTH,
    Interval,
    Point,
    INTERVAL_TIER,
    POINT_TIER,
)


def reSearch(pattern, string, flags=None) -> Match[str]:
    """Search for the string to match. Throws an error if no match is found."""
    if flags:
        matches = re.search(pattern, string, flags)
    else:
        matches = re.search(pattern, string)

    if not matches:
        raise errors.ParsingError("Expected field in Textgrid missing.")

    return matches


def _removeBlanks(tier: Dict) -> None:
    def hasContent(entry):
        return entry[-1] != ""

    tier["entries"] = filter(hasContent, tier["entries"])


def _removeUltrashortIntervals(
    tier: Dict, minLength: float, minTimestamp: float
) -> None:
    """
    Remove intervals that are very tiny

    Doing many small manipulations on intervals can lead to the creation
    of ultrashort intervals (e.g. 1*10^-15 seconds long).  This function
    removes such intervals.
    """

    # First, remove tiny intervals
    newEntryList: List[Interval] = []
    j = 0  # index to newEntryList
    for start, end, label in tier["entries"]:

        if end - start < minLength:
            # Correct ultra-short entries
            if len(newEntryList) > 0:
                lastStart, _, lastLabel = newEntryList[j - 1]
                newEntryList[j - 1] = Interval(lastStart, end, lastLabel)
        else:
            # Special case: the first entry in oldEntryList was ultra-short
            if len(newEntryList) == 0 and start != minTimestamp:
                newEntryList.append(Interval(minTimestamp, end, label))
            # Normal case
            else:
                newEntryList.append(Interval(start, end, label))
            j += 1

    # Next, shift near equivalent tiny boundaries
    # This will link intervals that were connected by an interval
    # that was shorter than minLength
    j = 0
    while j < len(newEntryList) - 1:
        diff = abs(newEntryList[j][1] - newEntryList[j + 1][0])
        if diff > 0 and diff < minLength:
            newEntryList[j] = Interval(
                newEntryList[j][0],
                newEntryList[j + 1][0],
                newEntryList[j][2],
            )
        j += 1

    tier["entries"] = newEntryList


def _fillInBlanks(
    tier: Dict,
    blankLabel: str = "",
    minTime: Optional[float] = None,
    maxTime: Optional[float] = None,
) -> None:
    """
    Fills in the space between intervals with empty space

    This is necessary to do when saving to create a well-formed textgrid
    """
    if minTime is None:
        minTime = tier["xmin"]

    if maxTime is None:
        maxTime = tier["xmax"]

    # Special case: empty textgrid
    if len(tier["entries"]) == 0:
        tier["entries"].append((minTime, maxTime, blankLabel))

    # Create a new entry list
    entryList = tier["entries"]
    entry = entryList[0]
    prevEnd = float(entry[1])
    newEntryList = [entry]
    for entry in entryList[1:]:
        newStart = float(entry[0])
        newEnd = float(entry[1])

        if prevEnd < newStart:
            newEntryList.append((prevEnd, newStart, blankLabel))
        newEntryList.append(entry)

        prevEnd = newEnd

    # Special case: If there is a gap at the start of the file
    if float(newEntryList[0][0]) < float(minTime):
        raise errors.ParsingError(
            "The entries are shorter than the min time specified in the textgrid."
        )
    if float(newEntryList[0][0]) > float(minTime):
        newEntryList.insert(0, (minTime, newEntryList[0][0], blankLabel))

    # Special case -- if there is a gap at the end of the file
    if maxTime is not None:
        if float(newEntryList[-1][1]) > float(maxTime):
            raise errors.ParsingError(
                "The entries are longer than the max time specified in the textgrid."
            )
        if float(newEntryList[-1][1]) < float(maxTime):
            newEntryList.append((newEntryList[-1][1], maxTime, blankLabel))

    newEntryList.sort()
    tier["entries"] = newEntryList


def parseTextgridStr(data: str, includeEmptyIntervals: bool = False) -> Dict:
    """
    Converts a string representation of a Textgrid into a dictionary

    Args:
        fnFullPath (str): the path to the textgrid to open
        includeEmptyIntervals (bool): if False, points and intervals with
             an empty label '' are not included in the returned dictionary

    Returns:
        Dictionary

    https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html
    """

    try:
        tgAsDict = json.loads(data)
    except ValueError:
        caseA = "ooTextFile short" in data
        caseB = "item [" not in data
        if caseA or caseB:
            tgAsDict = _parseShortTextgrid(data)
        else:
            tgAsDict = _parseNormalTextgrid(data)

    if includeEmptyIntervals is False:
        for tier in tgAsDict["tiers"]:
            _removeBlanks(tier)

    return tgAsDict


def getTextgridAsStr(
    tg: Dict,
    format: Literal["short_textgrid", "long_textgrid", "json"],
    includeBlankSpaces: bool,
    minTimestamp: Optional[float] = None,
    maxTimestamp: Optional[float] = None,
    minimumIntervalLength: float = MIN_INTERVAL_LENGTH,
) -> str:
    """
    Converts a textgrid to a string, suitable for saving

    Args:
        tg (Textgrid): the textgrid to convert to a string
        format (str): one of ['short_textgrid', 'long_textgrid', 'json']
        includeBlankSpaces (bool): if True, blank sections in interval
            tiers will be filled in with an empty interval
            (with a label of "")
        minTimestamp (float): the minTimestamp of the saved Textgrid;
            if None, use whatever is defined in the Textgrid object.
            If minTimestamp is larger than timestamps in your textgrid,
            an exception will be thrown.
        maxTimestamp (float): the maxTimestamp of the saved Textgrid;
            if None, use whatever is defined in the Textgrid object.
            If maxTimestamp is smaller than timestamps in your textgrid,
            an exception will be thrown.
        minimumIntervalLength (float): any labeled intervals smaller
            than this will be removed, useful for removing ultrashort
            or fragmented intervals; if None, don't remove any.
            Removed intervals are merged (without their label) into
            adjacent entries.

    Returns:
        a string representation of the textgrid
    """

    validFormats = [
        TextgridFormats.LONG_TEXTGRID,
        TextgridFormats.SHORT_TEXTGRID,
        TextgridFormats.JSON,
    ]
    if format not in validFormats:
        raise errors.WrongOption("format", format, validFormats)

    tg = _prepTgForSaving(
        tg, includeBlankSpaces, minTimestamp, maxTimestamp, minimumIntervalLength
    )

    if format == TextgridFormats.LONG_TEXTGRID:
        outputTxt = _tgToLongTextForm(tg)
    elif format == TextgridFormats.SHORT_TEXTGRID:
        outputTxt = _tgToShortTextForm(tg)
    elif format == TextgridFormats.JSON:
        outputTxt = _tgToJson(tg)

    return outputTxt


def _sortEntries(tg: Dict) -> None:
    for tier in tg["tiers"]:
        tier["entries"] = sorted(tier["entries"])


def _prepTgForSaving(
    tg: Dict,
    includeBlankSpaces: Optional[bool],
    minTimestamp: Optional[float],
    maxTimestamp: Optional[float],
    minimumIntervalLength: float,
) -> Dict:
    _sortEntries(tg)

    if minTimestamp is None:
        minTimestamp = tg["xmin"]
    else:
        tg["xmin"] = minTimestamp

    if maxTimestamp is None:
        maxTimestamp = tg["xmax"]
    else:
        tg["xmax"] = maxTimestamp

    # Fill in the blank spaces for interval tiers
    if includeBlankSpaces:
        newTierList = []
        for tier in tg["tiers"]:
            if tier["class"] == POINT_TIER:
                newTierList.append(tier)
                continue

            _fillInBlanks(tier, "", minTimestamp, maxTimestamp)
            if minimumIntervalLength is not None:
                _removeUltrashortIntervals(tier, minimumIntervalLength, minTimestamp)

    _sortEntries(tg)

    return tg


def _tgToShortTextForm(
    tg: Dict,
) -> str:

    # Header
    outputTxt = ""
    outputTxt += 'File type = "ooTextFile"\n'
    outputTxt += 'Object class = "TextGrid"\n\n'
    outputTxt += "%s\n%s\n" % (
        my_math.numToStr(tg["xmin"]),
        my_math.numToStr(tg["xmax"]),
    )
    outputTxt += "<exists>\n%d\n" % len(tg["tiers"])
    for tier in tg["tiers"]:
        text = ""
        text += '"%s"\n' % tier["class"]
        text += '"%s"\n' % utils.escapeQuotes(tier["name"])
        text += "%s\n%s\n%s\n" % (
            my_math.numToStr(tier["xmin"]),
            my_math.numToStr(tier["xmax"]),
            len(tier["entries"]),
        )

        for entry in tier["entries"]:
            entry = [my_math.numToStr(val) for val in entry[:-1]] + [
                '"%s"' % utils.escapeQuotes(entry[-1])
            ]

            text += "\n".join([str(val) for val in entry]) + "\n"

        outputTxt += text

    return outputTxt


def _tgToLongTextForm(tg: Dict) -> str:
    outputTxt = ""
    outputTxt += 'File type = "ooTextFile"\n'
    outputTxt += 'Object class = "TextGrid"\n\n'

    tab = " " * 4

    # Header
    outputTxt += "xmin = %s \n" % my_math.numToStr(tg["xmin"])
    outputTxt += "xmax = %s \n" % my_math.numToStr(tg["xmax"])
    outputTxt += "tiers? <exists> \n"
    outputTxt += "size = %d \n" % len(tg["tiers"])
    outputTxt += "item []: \n"

    for tierNum, tier in enumerate(tg["tiers"]):
        # Interval header
        outputTxt += tab + "item [%d]:\n" % (tierNum + 1)
        outputTxt += tab * 2 + 'class = "%s" \n' % tier["class"]
        outputTxt += tab * 2 + 'name = "%s" \n' % utils.escapeQuotes(tier["name"])
        outputTxt += tab * 2 + "xmin = %s \n" % my_math.numToStr(tier["xmin"])
        outputTxt += tab * 2 + "xmax = %s \n" % my_math.numToStr(tier["xmax"])

        entries = tier["entries"]
        if tier["class"] == INTERVAL_TIER:
            outputTxt += tab * 2 + "intervals: size = %d \n" % len(entries)
            for intervalNum, entry in enumerate(entries):
                start, end, label = entry
                outputTxt += tab * 2 + "intervals [%d]:\n" % (intervalNum + 1)
                outputTxt += tab * 3 + "xmin = %s \n" % my_math.numToStr(start)
                outputTxt += tab * 3 + "xmax = %s \n" % my_math.numToStr(end)
                outputTxt += tab * 3 + 'text = "%s" \n' % utils.escapeQuotes(label)
        else:
            outputTxt += tab * 2 + "points: size = %d \n" % len(entries)
            for pointNum, entry in enumerate(entries):
                timestamp, label = entry
                outputTxt += tab * 2 + "points [%d]:\n" % (pointNum + 1)
                outputTxt += tab * 3 + "number = %s \n" % my_math.numToStr(timestamp)
                outputTxt += tab * 3 + 'mark = "%s" \n' % utils.escapeQuotes(label)

    return outputTxt


def _tgToJson(tgAsDict: Dict) -> str:
    """Returns a json representation of a textgrid"""
    return json.dumps(tgAsDict, ensure_ascii=False)


def _parseNormalTextgrid(data: str) -> Dict:
    """
    Reads a normal textgrid
    """
    data = data.replace("\r\n", "\n")

    # Toss textgrid header
    header, data = re.split(r"item ?\[", data, maxsplit=1, flags=re.MULTILINE)

    headerList = header.split("\n")
    tgMin = float(headerList[3].split("=")[1].strip())
    tgMax = float(headerList[4].split("=")[1].strip())

    # Process each tier individually (will be output to separate folders)
    tiers = []
    tierList = re.split(r"item ?\[", data, flags=re.MULTILINE)[1:]
    for tierTxt in tierList:
        if 'class = "IntervalTier"' in tierTxt:
            tierType = INTERVAL_TIER
            searchWord = r"intervals ?\["
        else:
            tierType = POINT_TIER
            searchWord = r"points ?\["

        # Get tier meta-information
        try:
            d = re.split(searchWord, tierTxt, flags=re.MULTILINE)
            header, tierData = d[0], d[1:]
        except ValueError:
            # A tier with no entries
            if re.search(r"size ?= ?0", tierTxt):
                header = tierTxt
                tierData = []
            else:
                raise
        tierName = reSearch(
            r"name ?= ?\"(.*)\"\s*$", header, flags=re.MULTILINE
        ).groups()[0]
        tierName = re.sub(r'""', '"', tierName)

        tierStartTimeStr = reSearch(
            r"xmin ?= ?([\d.]+)\s*$", header, flags=re.MULTILINE
        ).groups()[0]
        tierStartTime = utils.strToIntOrFloat(tierStartTimeStr)

        tierEndTimeStr = reSearch(
            r"xmax ?= ?([\d.]+)\s*$", header, flags=re.MULTILINE
        ).groups()[0]
        tierEndTime = utils.strToIntOrFloat(tierEndTimeStr)

        # Get the tier entry list
        entryList: List[Any] = []
        if tierType == INTERVAL_TIER:
            for element in tierData:
                timeStart = reSearch(
                    r"xmin ?= ?([\d.]+)\s*$", element, flags=re.MULTILINE
                ).groups()[0]
                timeEnd = reSearch(
                    r"xmax ?= ?([\d.]+)\s*$", element, flags=re.MULTILINE
                ).groups()[0]
                label = reSearch(
                    r"text ?= ?\"(.*)\"\s*$",
                    element,
                    flags=re.MULTILINE | re.DOTALL,
                ).groups()[0]

                label = label.strip()
                label = re.sub(r'""', '"', label)
                entryList.append(Interval(timeStart, timeEnd, label))
        else:
            for element in tierData:
                time = reSearch(
                    r"number ?= ?([\d.]+)\s*$", element, flags=re.MULTILINE
                ).groups()[0]
                label = reSearch(
                    r"mark ?= ?\"(.*)\"\s*$",
                    element,
                    flags=re.MULTILINE | re.DOTALL,
                ).groups()[0]
                label = label.strip()
                entryList.append(Point(time, label))

        tierDict = {
            "class": tierType,
            "name": tierName,
            "xmin": float(tierStartTime),
            "xmax": float(tierEndTime),
            "entries": entryList,
        }
        tiers.append(tierDict)

    tgDict = {"xmin": tgMin, "xmax": tgMax, "tiers": tiers}

    return tgDict


def _parseShortTextgrid(data: str) -> Dict:
    """
    Reads a short textgrid file
    """
    data = data.replace("\r\n", "\n")

    intervalIndicies = [(i, True) for i in utils.findAll(data, '"IntervalTier"')]
    pointIndicies = [(i, False) for i in utils.findAll(data, '"TextTier"')]

    indexList = [*intervalIndicies, *pointIndicies]
    indexList.append((len(data), True))  # The 'end' of the file
    indexList.sort()

    tupleList = [
        (indexList[i][0], indexList[i + 1][0], indexList[i][1])
        for i in range(len(indexList) - 1)
    ]

    # Set the textgrid's min and max times
    header = data[: tupleList[0][0]]
    headerList = header.split("\n")
    tgMin = float(headerList[3].strip())
    tgMax = float(headerList[4].strip())

    # Load the data for each tier
    tiers = []
    for blockStartI, blockEndI, isInterval in tupleList:
        tierData = data[blockStartI:blockEndI]

        # First row contains the tier type, which we already know
        metaStartI = _fetchRow(tierData, 0)[1]

        # Tier meta-information
        tierName, tierNameEndI = _fetchTextRow(tierData, metaStartI)
        tierStartTimeStr, tierStartTimeI = _fetchRow(tierData, tierNameEndI)
        tierEndTimeStr, tierEndTimeI = _fetchRow(tierData, tierStartTimeI)
        startTimeI = _fetchRow(tierData, tierEndTimeI)[1]

        tierStartTime = utils.strToIntOrFloat(tierStartTimeStr)
        tierEndTime = utils.strToIntOrFloat(tierEndTimeStr)

        # Tier entry data
        entryList: List[Any] = []
        if isInterval:
            className = INTERVAL_TIER
            while True:
                try:
                    startTime, endTimeI = _fetchRow(tierData, startTimeI)
                    endTime, labelI = _fetchRow(tierData, endTimeI)
                    label, startTimeI = _fetchTextRow(tierData, labelI)
                except (ValueError, IndexError):
                    break

                label = label.strip()
                entryList.append(Interval(startTime, endTime, label))
        else:
            className = POINT_TIER
            while True:
                try:
                    time, labelI = _fetchRow(tierData, startTimeI)
                    label, startTimeI = _fetchTextRow(tierData, labelI)
                except (ValueError, IndexError):
                    break
                label = label.strip()
                entryList.append(Point(time, label))

        tierDict = {
            "class": className,
            "name": tierName,
            "xmin": float(tierStartTime),
            "xmax": float(tierEndTime),
            "entries": entryList,
        }
        tiers.append(tierDict)

    tgDict = {"xmin": tgMin, "xmax": tgMax, "tiers": tiers}

    return tgDict


def _fetchRow(
    dataStr: str, index: int, searchStr: Optional[str] = None
) -> Tuple[str, int]:
    if searchStr is None:
        startIndex = index
    else:
        startIndex = dataStr.index(searchStr, index) + len(searchStr)

    endIndex = dataStr.index("\n", startIndex)

    word = dataStr[startIndex:endIndex]
    word = word.strip()
    if word[0] == '"' and word[-1] == '"':
        word = word[1:-1]
    word = word.strip()

    return word, endIndex + 1


def _fetchTextRow(
    dataStr: str, index: int, searchStr: Optional[str] = None
) -> Tuple[str, int]:
    if searchStr is None:
        startIndex = index
    else:
        startIndex = dataStr.index(searchStr, index) + len(searchStr)

    # A textgrid text is ended by double quotes. Double quotes that
    # appear in the text are escaped by a preceeding double quotes.
    # We know we're at the end of a text if the number of double
    # quotes is odd.
    endIndex = startIndex + 1
    while True:
        quoteStartIndex = dataStr.index('"', endIndex)
        quoteEndIndex = quoteStartIndex
        while dataStr[quoteEndIndex] == '"':
            quoteEndIndex += 1

        endIndex = quoteEndIndex

        if (quoteEndIndex - quoteStartIndex) % 2 != 0:
            break

    word = dataStr[startIndex:endIndex]
    word = word[1:-1]  # Remove the quote marks around the text
    word = word.strip()

    word = word.replace('""', '"')  # Unescape quote marks

    # Advance to the end of the line
    endIndex = dataStr.index("\n", endIndex)

    return word, endIndex + 1
