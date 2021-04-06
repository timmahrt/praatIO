import io
import json

from praatio import textgrid
from praatio.utilities import utils
from praatio.utilities import myMath

MIN_INTERVAL_LENGTH = 0.00000001  # Arbitrary threshold

TEXTGRID = "textgrid"
JSON = "json"
SUPPORTED_OUTPUT_FORMATS = [TEXTGRID, JSON]


def _removeBlanks(tier):
    entryList = [entry for entry in tier.entryList if entry[-1] != ""]
    return tier.new(entryList=entryList)


def _removeUltrashortIntervals(tier, minLength, minTimestamp):
    """
    Remove intervals that are very tiny

    Doing many small manipulations on intervals can lead to the creation
    of ultrashort intervals (e.g. 1*10^-15 seconds long).  This function
    removes such intervals.
    """

    # First, remove tiny intervals
    newEntryList = []
    j = 0  # index to newEntryList
    for start, stop, label in tier.entryList:

        if stop - start < minLength:
            # Correct ultra-short entries
            if len(newEntryList) > 0:
                lastStart, _, lastLabel = newEntryList[j - 1]
                newEntryList[j - 1] = (lastStart, stop, lastLabel)
        else:
            # Special case: the first entry in oldEntryList was ultra-short
            if len(newEntryList) == 0 and start != minTimestamp:
                newEntryList.append((minTimestamp, stop, label))
            # Normal case
            else:
                newEntryList.append((start, stop, label))
            j += 1

    # Next, shift near equivalent tiny boundaries
    # This will link intervals that were connected by an interval
    # that was shorter than minLength
    j = 0
    while j < len(newEntryList) - 1:
        diff = abs(newEntryList[j][1] - newEntryList[j + 1][0])
        if diff > 0 and diff < minLength:
            newEntryList[j] = (
                newEntryList[j][0],
                newEntryList[j + 1][0],
                newEntryList[j][2],
            )
        j += 1

    return tier.new(entryList=newEntryList)


def _fillInBlanks(tier, blankLabel="", startTime=None, endTime=None):
    """
    Fills in the space between intervals with empty space

    This is necessary to do when saving to create a well-formed textgrid
    """
    if startTime is None:
        startTime = tier.minTimestamp

    if endTime is None:
        endTime = tier.maxTimestamp

    # Special case: empty textgrid
    if len(tier.entryList) == 0:
        tier.entryList.append((startTime, endTime, blankLabel))

    # Create a new entry list
    entryList = tier.entryList[:]
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

    return tier.new(entryList=newEntryList)


def _escapeQuotes(text):
    return text.replace('"', '""')


def openTextgrid(fnFullPath, readRaw=False, readAsJson=False):
    """
    Opens a textgrid for editing

    Args:
        fnFullPath (str): the path to the textgrid to open
        readRaw (bool): points and intervals with an empty label
            '' are removed unless readRaw=True
        readAsJson (bool): if True, assume the Textgrid is saved
            as Json rather than in its native format

    Returns:
        Textgrid

    https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html
    """
    try:
        with io.open(fnFullPath, "r", encoding="utf-16") as fd:
            data = fd.read()
    except UnicodeError:
        with io.open(fnFullPath, "r", encoding="utf-8") as fd:
            data = fd.read()

    if readAsJson:
        tgAsDict = json.loads(data)
        textgrid = _dictionaryToTg(tgAsDict)
    else:
        caseA = "ooTextFile short" in data
        caseB = "item [" not in data
        if caseA or caseB:
            textgrid = _parseShortTextgrid(data)
        else:
            textgrid = _parseNormalTextgrid(data)

    if readRaw == False:
        for tierName in textgrid.tierNameList:
            tier = textgrid.tierDict[tierName]
            tier = _removeBlanks(tier)
            textgrid.replaceTier(tierName, tier)

    return textgrid


def saveTextgrid(
    tg,
    fn,
    minimumIntervalLength=MIN_INTERVAL_LENGTH,
    minTimestamp=None,
    maxTimestamp=None,
    useShortForm=True,
    outputFormat=TEXTGRID,
    ignoreBlankSpaces=False,
):
    """
    To save the current textgrid

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
        useShortForm (bool): if True, save the textgrid as a short
            textgrid. Otherwise, use the long-form textgrid format.
            For backwards compatibility, is True by default. Ignored if
            format is not 'Textgrid'
        outputFormat (str): one of ['textgrid', 'json']
        ignoreBlankSpaces (bool): if False, blank sections in interval
            tiers will be filled in with an empty interval
            (with a label of "")

    Returns:
        None
    """

    if outputFormat not in SUPPORTED_OUTPUT_FORMATS:
        raise BadFormatException(outputFormat, SUPPORTED_OUTPUT_FORMATS)

    if outputFormat == TEXTGRID:
        if useShortForm:
            outputTxt = _tgToShortTextForm(
                tg,
                minimumIntervalLength,
                minTimestamp,
                maxTimestamp,
                ignoreBlankSpaces,
            )
        else:
            outputTxt = _tgToLongTextForm(
                tg,
                minimumIntervalLength,
                minTimestamp,
                maxTimestamp,
                ignoreBlankSpaces,
            )
    elif outputFormat == JSON:
        outputTxt = _tgToJson(
            tg,
            minimumIntervalLength,
            minTimestamp,
            maxTimestamp,
            ignoreBlankSpaces,
        )

    with io.open(fn, "w", encoding="utf-8") as fd:
        fd.write(outputTxt)


def _prepTgForSaving(
    tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces
):
    for tier in tg.tierDict.values():
        tier.sort()

    if minTimestamp is None:
        minTimestamp = tg.minTimestamp
    else:
        tg.minTimestamp = minTimestamp

    if maxTimestamp is None:
        maxTimestamp = tg.maxTimestamp
    else:
        tg.maxTimestamp = maxTimestamp

    # Fill in the blank spaces for interval tiers
    if not ignoreBlankSpaces:
        for name in tg.tierNameList:
            tier = tg.tierDict[name]
            if isinstance(tier, textgrid.IntervalTier):
                tier = _fillInBlanks(tier, "", minTimestamp, maxTimestamp)
                if minimumIntervalLength is not None:
                    tier = _removeUltrashortIntervals(
                        tier, minimumIntervalLength, minTimestamp
                    )
                tg.tierDict[name] = tier

    for tier in tg.tierDict.values():
        tier.sort()

    return tg


def _tgToShortTextForm(
    tg,
    minimumIntervalLength=MIN_INTERVAL_LENGTH,
    minTimestamp=None,
    maxTimestamp=None,
    ignoreBlankSpaces=False,
):
    tg = _prepTgForSaving(
        tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces
    )

    # Header
    outputTxt = ""
    outputTxt += 'File type = "ooTextFile"\n'
    outputTxt += 'Object class = "TextGrid"\n\n'
    outputTxt += "%s\n%s\n" % (
        myMath.numToStr(tg.minTimestamp),
        myMath.numToStr(tg.maxTimestamp),
    )
    outputTxt += "<exists>\n%d\n" % len(tg.tierNameList)
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]
        text = ""
        text += '"%s"\n' % tier.tierType
        text += '"%s"\n' % _escapeQuotes(tier.name)
        text += "%s\n%s\n%s\n" % (
            myMath.numToStr(tier.minTimestamp),
            myMath.numToStr(tier.maxTimestamp),
            len(tier.entryList),
        )

        for entry in tier.entryList:
            entry = [myMath.numToStr(val) for val in entry[:-1]] + [
                '"%s"' % _escapeQuotes(entry[-1])
            ]
            try:
                unicode
            except NameError:
                unicodeFunc = str
            else:
                unicodeFunc = unicode

            text += "\n".join([unicodeFunc(val) for val in entry]) + "\n"

        outputTxt += text

    return outputTxt


def _tgToLongTextForm(
    tg,
    minimumIntervalLength=MIN_INTERVAL_LENGTH,
    minTimestamp=None,
    maxTimestamp=None,
    ignoreBlankSpaces=False,
):
    tg = _prepTgForSaving(
        tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces
    )
    outputTxt = ""
    outputTxt += 'File type = "ooTextFile"\n'
    outputTxt += 'Object class = "TextGrid"\n\n'

    tab = " " * 4

    # Header
    outputTxt += "xmin = %s \n" % myMath.numToStr(tg.minTimestamp)
    outputTxt += "xmax = %s \n" % myMath.numToStr(tg.maxTimestamp)
    outputTxt += "tiers? <exists> \n"
    outputTxt += "size = %d \n" % len(tg.tierNameList)
    outputTxt += "item []: \n"

    for tierNum, tierName in enumerate(tg.tierNameList):
        tier = tg.tierDict[tierName]
        # Interval header
        outputTxt += tab + "item [%d]:\n" % (tierNum + 1)
        outputTxt += tab * 2 + 'class = "%s" \n' % tier.tierType
        outputTxt += tab * 2 + 'name = "%s" \n' % _escapeQuotes(tierName)
        outputTxt += tab * 2 + "xmin = %s \n" % myMath.numToStr(tier.minTimestamp)
        outputTxt += tab * 2 + "xmax = %s \n" % myMath.numToStr(tier.maxTimestamp)

        if tier.tierType == textgrid.INTERVAL_TIER:
            outputTxt += tab * 2 + "intervals: size = %d \n" % len(tier.entryList)
            for intervalNum, entry in enumerate(tier.entryList):
                start, stop, label = entry
                outputTxt += tab * 2 + "intervals [%d]:\n" % (intervalNum + 1)
                outputTxt += tab * 3 + "xmin = %s \n" % myMath.numToStr(start)
                outputTxt += tab * 3 + "xmax = %s \n" % myMath.numToStr(stop)
                outputTxt += tab * 3 + 'text = "%s" \n' % _escapeQuotes(label)
        else:
            outputTxt += tab * 2 + "points: size = %d \n" % len(tier.entryList)
            for pointNum, entry in enumerate(tier.entryList):
                timestamp, label = entry
                outputTxt += tab * 2 + "points [%d]:\n" % (pointNum + 1)
                outputTxt += tab * 3 + "number = %s \n" % myMath.numToStr(timestamp)
                outputTxt += tab * 3 + 'mark = "%s" \n' % _escapeQuotes(label)

    return outputTxt


def _tgToJson(tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces):
    """Returns a json representation of a textgrid"""
    tg = _prepTgForSaving(
        tg, minimumIntervalLength, minTimestamp, maxTimestamp, ignoreBlankSpaces
    )
    tgAsDict = _tgToDictionary(tg)
    return json.dumps(tgAsDict, ensure_ascii=False)


def _tgToDictionary(tg):
    tiers = []
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]
        tierDict = {
            "class": tier.tierType,
            "name": tierName,
            "xmin": tier.minTimestamp,
            "xmax": tier.maxTimestamp,
            "entries": tier.entryList,
        }
        tiers.append(tierDict)

    tgAsDict = {"xmin": tg.minTimestamp, "xmax": tg.maxTimestamp, "tiers": tiers}

    return tgAsDict


def _dictionaryToTg(tgAsDict):
    """Converts a dictionary representation of a textgrid to a Textgrid"""
    tg = textgrid.Textgrid()
    tg.minTimestamp = tgAsDict["xmin"]
    tg.maxTimestamp = tgAsDict["xmax"]

    for tierAsDict in tgAsDict["tiers"]:
        if tierAsDict["class"] == textgrid.INTERVAL_TIER:
            klass = textgrid.IntervalTier
        else:
            klass = textgrid.PointTier
        tier = klass(
            tierAsDict["name"],
            tierAsDict["entries"],
            tierAsDict["xmin"],
            tierAsDict["xmax"],
        )
        tg.addTier(tier)

    return tg


def _parseNormalTextgrid(data):
    """
    Reads a normal textgrid
    """
    data = data.replace("\r\n", "\n")

    newTG = textgrid.Textgrid()

    # Toss textgrid header
    header, data = data.split("item [", 1)

    headerList = header.split("\n")
    tgMin = float(headerList[3].split("=")[1].strip())
    tgMax = float(headerList[4].split("=")[1].strip())

    newTG.minTimestamp = tgMin
    newTG.maxTimestamp = tgMax

    # Process each tier individually (will be output to separate folders)
    tierList = data.split("item [")[1:]
    for tierTxt in tierList:

        hasData = True

        if 'class = "IntervalTier"' in tierTxt:
            tierType = textgrid.INTERVAL_TIER
            searchWord = "intervals ["
        else:
            tierType = textgrid.POINT_TIER
            searchWord = "points ["

        # Get tier meta-information
        try:
            header, tierData = tierTxt.split(searchWord, 1)
        except ValueError:
            # A tier with no entries
            if "size = 0" in tierTxt:
                header = tierTxt
                tierData = ""
                hadData = False
            else:
                raise
        tierName = header.split("name = ")[1].split("\n", 1)[0]
        tierName, tierNameI = _fetchTextRow(header, 0, "name = ")
        tierStart = header.split("xmin = ")[1].split("\n", 1)[0]
        tierStart = strToIntOrFloat(tierStart)
        tierEnd = header.split("xmax = ")[1].split("\n", 1)[0]
        tierEnd = strToIntOrFloat(tierEnd)

        # Get the tier entry list
        tierEntryList = []
        labelI = 0
        if tierType == textgrid.INTERVAL_TIER:
            while True:
                try:
                    timeStart, timeStartI = _fetchRow(tierData, labelI, "xmin = ")
                    timeEnd, timeEndI = _fetchRow(tierData, timeStartI, "xmax = ")
                    label, labelI = _fetchTextRow(tierData, timeEndI, "text = ")
                except (ValueError, IndexError):
                    break

                label = label.strip()
                tierEntryList.append((timeStart, timeEnd, label))
            tier = textgrid.IntervalTier(tierName, tierEntryList, tierStart, tierEnd)
        else:
            while True:
                try:
                    time, timeI = _fetchRow(tierData, labelI, "number = ")
                    label, labelI = _fetchTextRow(tierData, timeI, "mark = ")
                except (ValueError, IndexError):
                    break

                label = label.strip()
                tierEntryList.append((time, label))
            tier = textgrid.PointTier(tierName, tierEntryList, tierStart, tierEnd)

        newTG.addTier(tier)

    return newTG


def _parseShortTextgrid(data):
    """
    Reads a short textgrid file
    """
    data = data.replace("\r\n", "\n")

    newTG = textgrid.Textgrid()

    intervalIndicies = [(i, True) for i in utils.findAll(data, '"IntervalTier"')]
    pointIndicies = [(i, False) for i in utils.findAll(data, '"TextTier"')]

    indexList = intervalIndicies + pointIndicies
    indexList.append((len(data), None))  # The 'end' of the file
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

    newTG.minTimestamp = tgMin
    newTG.maxTimestamp = tgMax

    # Load the data for each tier
    for blockStartI, blockEndI, isInterval in tupleList:
        tierData = data[blockStartI:blockEndI]

        # First row contains the tier type, which we already know
        metaStartI = _fetchRow(tierData, 0)[1]

        # Tier meta-information
        tierName, tierNameEndI = _fetchTextRow(tierData, metaStartI)
        tierStartTime, tierStartTimeI = _fetchRow(tierData, tierNameEndI)
        tierEndTime, tierEndTimeI = _fetchRow(tierData, tierStartTimeI)
        startTimeI = _fetchRow(tierData, tierEndTimeI)[1]

        tierStartTime = strToIntOrFloat(tierStartTime)
        tierEndTime = strToIntOrFloat(tierEndTime)

        # Tier entry data
        entryList = []
        if isInterval:
            while True:
                try:
                    startTime, endTimeI = _fetchRow(tierData, startTimeI)
                    endTime, labelI = _fetchRow(tierData, endTimeI)
                    label, startTimeI = _fetchTextRow(tierData, labelI)
                except (ValueError, IndexError):
                    break

                label = label.strip()
                entryList.append((startTime, endTime, label))

            newTG.addTier(
                textgrid.IntervalTier(tierName, entryList, tierStartTime, tierEndTime)
            )

        else:
            while True:
                try:
                    time, labelI = _fetchRow(tierData, startTimeI)
                    label, startTimeI = _fetchTextRow(tierData, labelI)
                except (ValueError, IndexError):
                    break
                label = label.strip()
                entryList.append((time, label))

            newTG.addTier(
                textgrid.PointTier(tierName, entryList, tierStartTime, tierEndTime)
            )

    return newTG


def strToIntOrFloat(inputStr):
    return float(inputStr) if "." in inputStr else int(inputStr)


def _fetchRow(dataStr, index, searchStr=None):
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


def _fetchTextRow(dataStr, index, searchStr=None):
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
