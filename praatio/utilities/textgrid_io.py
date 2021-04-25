import json
from typing import Optional, Tuple, List, Any, Dict

from praatio.utilities import errors
from praatio.utilities import utils
from praatio.utilities import myMath
from praatio.utilities.constants import (
    LONG_TEXTGRID,
    SHORT_TEXTGRID,
    JSON,
    MIN_INTERVAL_LENGTH,
    Interval,
    Point,
    INTERVAL_TIER,
    POINT_TIER,
)

SUPPORTED_OUTPUT_FORMATS = [LONG_TEXTGRID, SHORT_TEXTGRID, JSON]


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
    for start, stop, label in tier["entries"]:

        if stop - start < minLength:
            # Correct ultra-short entries
            if len(newEntryList) > 0:
                lastStart, _, lastLabel = newEntryList[j - 1]
                newEntryList[j - 1] = Interval(lastStart, stop, lastLabel)
        else:
            # Special case: the first entry in oldEntryList was ultra-short
            if len(newEntryList) == 0 and start != minTimestamp:
                newEntryList.append(Interval(minTimestamp, stop, label))
            # Normal case
            else:
                newEntryList.append(Interval(start, stop, label))
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
    startTime: Optional[float] = None,
    endTime: Optional[float] = None,
) -> None:
    """
    Fills in the space between intervals with empty space

    This is necessary to do when saving to create a well-formed textgrid
    """
    if startTime is None:
        startTime = tier["xmin"]

    if endTime is None:
        endTime = tier["xmax"]

    # Special case: empty textgrid
    if len(tier["entries"]) == 0:
        tier["entries"].append((startTime, endTime, blankLabel))

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
    assert float(newEntryList[0][0]) >= float(startTime)
    if float(newEntryList[0][0]) > float(startTime):
        newEntryList.insert(0, (startTime, newEntryList[0][0], blankLabel))

    # Special case -- if there is a gap at the end of the file
    if endTime is not None:
        assert float(newEntryList[-1][1]) <= float(endTime)
        if float(newEntryList[-1][1]) < float(endTime):
            newEntryList.append((newEntryList[-1][1], endTime, blankLabel))

    newEntryList.sort()
    tier["entries"] = newEntryList


def parseTextgridStr(data: str, readRaw: bool = False) -> Dict:
    """
    Converts a string representation of a Textgrid into a dictionary

    Args:
        fnFullPath (str): the path to the textgrid to open
        readRaw (bool): points and intervals with an empty label
            '' are removed unless readRaw=True
        readAsJson (bool): if True, assume the Textgrid is saved
            as Json rather than in its native format

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

    if readRaw is False:
        for tier in tgAsDict["tiers"]:
            _removeBlanks(tier)

    return tgAsDict


def getTextgridAsStr(
    tg: Dict,
    minimumIntervalLength: float = MIN_INTERVAL_LENGTH,
    minTimestamp: Optional[float] = None,
    maxTimestamp: Optional[float] = None,
    outputFormat: str = SHORT_TEXTGRID,
    ignoreBlankSpaces: bool = False,
) -> str:
    """
    Converts a textgrid to a string, suitable for saving

    Args:
        fn (str): the fullpath filename of the output
        minimumIntervalLength (float): any labeled intervals smaller
            than this will be removed, useful for removing ultrashort
            or fragmented intervals; if None, don't remove any.
            Removed intervals are merged (without their label) into
            adjacent entries.
        minTimestamp (float): the minTimestamp of the saved Textgrid;
            if None, use whatever is defined in the Textgrid object.
            If minTimestamp is larger than timestamps in your textgrid,
            an exception will be thrown.
        maxTimestamp (float): the maxTimestamp of the saved Textgrid;
            if None, use whatever is defined in the Textgrid object.
            If maxTimestamp is smaller than timestamps in your textgrid,
            an exception will be thrown.
        outputFormat (str): one of ['short_textgrid', 'long_textgrid', 'json']
        ignoreBlankSpaces (bool): if False, blank sections in interval
            tiers will be filled in with an empty interval
            (with a label of "")

    Returns:
        None
    """

    if outputFormat not in SUPPORTED_OUTPUT_FORMATS:
        raise errors.BadFormatException(str(outputFormat), SUPPORTED_OUTPUT_FORMATS)

    tg = _prepTgForSaving(
        tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces
    )

    if outputFormat == LONG_TEXTGRID:
        outputTxt = _tgToLongTextForm(tg)
    elif outputFormat == SHORT_TEXTGRID:
        outputTxt = _tgToShortTextForm(tg)
    elif outputFormat == JSON:
        outputTxt = _tgToJson(tg)

    return outputTxt


def _sortEntries(tg: Dict) -> None:
    for tier in tg["tiers"]:
        tier["entries"] = sorted(tier["entries"])


def _prepTgForSaving(
    tg: Dict,
    minimumIntervalLength: float,
    minTimestamp: Optional[float],
    maxTimestamp: Optional[float],
    ignoreBlankSpaces: Optional[bool],
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
    if not ignoreBlankSpaces:
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
        myMath.numToStr(tg["xmin"]),
        myMath.numToStr(tg["xmax"]),
    )
    outputTxt += "<exists>\n%d\n" % len(tg["tiers"])
    for tier in tg["tiers"]:
        text = ""
        text += '"%s"\n' % tier["class"]
        text += '"%s"\n' % utils.escapeQuotes(tier["name"])
        text += "%s\n%s\n%s\n" % (
            myMath.numToStr(tier["xmin"]),
            myMath.numToStr(tier["xmax"]),
            len(tier["entries"]),
        )

        for entry in tier["entries"]:
            entry = [myMath.numToStr(val) for val in entry[:-1]] + [
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
    outputTxt += "xmin = %s \n" % myMath.numToStr(tg["xmin"])
    outputTxt += "xmax = %s \n" % myMath.numToStr(tg["xmax"])
    outputTxt += "tiers? <exists> \n"
    outputTxt += "size = %d \n" % len(tg["tiers"])
    outputTxt += "item []: \n"

    for tierNum, tier in enumerate(tg["tiers"]):
        # Interval header
        outputTxt += tab + "item [%d]:\n" % (tierNum + 1)
        outputTxt += tab * 2 + 'class = "%s" \n' % tier["class"]
        outputTxt += tab * 2 + 'name = "%s" \n' % utils.escapeQuotes(tier["name"])
        outputTxt += tab * 2 + "xmin = %s \n" % myMath.numToStr(tier["xmin"])
        outputTxt += tab * 2 + "xmax = %s \n" % myMath.numToStr(tier["xmax"])

        entries = tier["entries"]
        if tier["class"] == INTERVAL_TIER:
            outputTxt += tab * 2 + "intervals: size = %d \n" % len(entries)
            for intervalNum, entry in enumerate(entries):
                start, stop, label = entry
                outputTxt += tab * 2 + "intervals [%d]:\n" % (intervalNum + 1)
                outputTxt += tab * 3 + "xmin = %s \n" % myMath.numToStr(start)
                outputTxt += tab * 3 + "xmax = %s \n" % myMath.numToStr(stop)
                outputTxt += tab * 3 + 'text = "%s" \n' % utils.escapeQuotes(label)
        else:
            outputTxt += tab * 2 + "points: size = %d \n" % len(entries)
            for pointNum, entry in enumerate(entries):
                timestamp, label = entry
                outputTxt += tab * 2 + "points [%d]:\n" % (pointNum + 1)
                outputTxt += tab * 3 + "number = %s \n" % myMath.numToStr(timestamp)
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
    header, data = data.split("item [", 1)

    headerList = header.split("\n")
    tgMin = float(headerList[3].split("=")[1].strip())
    tgMax = float(headerList[4].split("=")[1].strip())

    # Process each tier individually (will be output to separate folders)
    tiers = []
    tierList = data.split("item [")[1:]
    for tierTxt in tierList:
        if 'class = "IntervalTier"' in tierTxt:
            tierType = INTERVAL_TIER
            searchWord = "intervals ["
        else:
            tierType = POINT_TIER
            searchWord = "points ["

        # Get tier meta-information
        try:
            header, tierData = tierTxt.split(searchWord, 1)
        except ValueError:
            # A tier with no entries
            if "size = 0" in tierTxt:
                header = tierTxt
                tierData = ""
            else:
                raise
        tierName = header.split("name = ")[1].split("\n", 1)[0]
        tierName, tierNameI = _fetchTextRow(header, 0, "name = ")
        tierStartStr = header.split("xmin = ")[1].split("\n", 1)[0]
        tierStartTime = utils.strToIntOrFloat(tierStartStr)
        tierEndStr = header.split("xmax = ")[1].split("\n", 1)[0]
        tierEndTime = utils.strToIntOrFloat(tierEndStr)

        # Get the tier entry list
        labelI = 0
        entryList: List[Any] = []
        if tierType == INTERVAL_TIER:
            while True:
                try:
                    timeStart, timeStartI = _fetchRow(tierData, labelI, "xmin = ")
                    timeEnd, timeEndI = _fetchRow(tierData, timeStartI, "xmax = ")
                    label, labelI = _fetchTextRow(tierData, timeEndI, "text = ")
                except (ValueError, IndexError):
                    break

                label = label.strip()
                entryList.append(Interval(timeStart, timeEnd, label))
        else:
            while True:
                try:
                    time, timeI = _fetchRow(tierData, labelI, "number = ")
                    label, labelI = _fetchTextRow(tierData, timeI, "mark = ")
                except (ValueError, IndexError):
                    break

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
