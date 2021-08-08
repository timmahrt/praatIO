"""
Common/generic scripts or utilities that extend the functionality of praatio

see **examples/correct_misaligned_tiers.py**, **examples/delete_vowels.py**,
**examples/extract_subwavs.py**, **examples/splice_example.py**.
"""

import os
from os.path import join
import math
import copy
from typing import Callable, List, Tuple, Optional

from typing_extensions import Literal, Final

from praatio import textgrid
from praatio import audio
from praatio.data_classes import textgrid_tier
from praatio.utilities import constants
from praatio.utilities.constants import Point, Interval
from praatio.utilities import errors


class NameStyle:
    APPEND = "append"
    APPEND_NO_I = "append_no_i"
    LABEL = "label"


def _shiftTimes(
    tg: textgrid.Textgrid, timeV: float, newTimeV: float
) -> textgrid.Textgrid:
    """
    Change all instances of timeV in the textgrid to newTimeV

    These are meant to be small changes.  No checks are done to see
    if the new interval steps on other intervals
    """
    tg = tg.new()
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]

        if isinstance(tier, textgrid.IntervalTier):
            entryList = [
                entry
                for entry in tier.entryList
                if entry[0] == timeV or entry[1] == timeV
            ]
            insertEntryList = []
            for entry in entryList:
                if entry[0] == timeV:
                    newStart, newStop = newTimeV, entry[1]
                elif entry[1] == timeV:
                    newStart, newStop = entry[0], newTimeV
                tier.deleteEntry(entry)
                insertEntryList.append((newStart, newStop, entry[2]))

            for entry in insertEntryList:
                tier.insertEntry(entry)

        elif isinstance(tier, textgrid.PointTier):
            entryList = [entry for entry in tier.entryList if entry[0] == timeV]
            for entry in entryList:
                tier.deleteEntry(entry)
                tier.insertEntry(Point(newTimeV, entry[1]))

    return tg


def audioSplice(
    audioObj: audio.WavObj,
    spliceSegment: audio.WavObj,
    tg: textgrid.Textgrid,
    tierName: str,
    newLabel: str,
    insertStart: float,
    insertStop: float = None,
    alignToZeroCrossing: bool = True,
) -> Tuple[audio.WavObj, textgrid.Textgrid]:
    """
    Splices a segment into an audio file and corresponding textgrid

    Args:
        audioObj (WavObj): the audio to splice into
        spliceSegment (WavObj): the audio segment that will be placed into a
            larger audio file
        tg (Textgrid): the textgrid to splice into
        tierName (str): the name of the tier that will receive the new label
        newLabel (str): the label for the splice interval on the tier with
            name tierName
        insertStart (float): the time to insert the splice
        insertStop (float): if not None, will erase the region between
            sourceSpStart and sourceSpEnd.  (In practice this means audioSplice
            removes one segment and inserts another in its place)
        alignToZeroCrossing - if True, moves all involved times to the nearest
            zero crossing in the audio.  Generally results
            in better sounding output

    Returns:
        [WavObj, Textgrid]
    """

    retTG = tg.new()

    # Ensure all time points involved in splicing fall on zero crossings
    if alignToZeroCrossing is True:

        # Cut the splice segment to zero crossings
        spliceDuration = spliceSegment.getDuration()
        spliceZeroStart = spliceSegment.findNearestZeroCrossing(0)
        spliceZeroEnd = spliceSegment.findNearestZeroCrossing(spliceDuration)
        spliceSegment = spliceSegment.getSubsegment(spliceZeroStart, spliceZeroEnd)

        # Move the textgrid borders to zero crossings
        oldInsertStart = insertStart
        insertStart = audioObj.findNearestZeroCrossing(oldInsertStart)
        retTG = _shiftTimes(retTG, oldInsertStart, insertStart)

        if insertStop is not None:
            oldInsertStop = insertStop
            insertStop = audioObj.findNearestZeroCrossing(oldInsertStop)
            retTG = _shiftTimes(retTG, oldInsertStop, insertStop)

    # Get the start time
    insertTime = insertStart
    if insertStop is not None:
        insertTime = insertStop

    # Insert into the audio file
    audioObj.insert(insertTime, spliceSegment.audioSamples)

    # Insert a blank region into the textgrid on all tiers
    targetDuration = spliceSegment.getDuration()
    retTG = retTG.insertSpace(insertTime, targetDuration, "stretch")

    # Insert the splice entry into the target tier
    newEntry = (insertTime, insertTime + targetDuration, newLabel)
    retTG.tierDict[tierName].insertEntry(newEntry)

    # Finally, delete the old section if requested
    if insertStop is not None:
        audioObj.deleteSegment(insertStart, insertStop)
        retTG = retTG.eraseRegion(insertStart, insertStop, doShrink=True)

    return audioObj, retTG


def spellCheckEntries(
    tg: textgrid.Textgrid,
    targetTierName: str,
    newTierName: str,
    checkFunction: Callable[[str], bool],
    printEntries: bool = False,
) -> textgrid.Textgrid:
    """
    Spell checks words in a textgrid

    Entries can contain one or more words, separated by whitespace.
    If a mispelling is found, it is noted in a special tier and optionally
    printed to the screen.

    checkFunction is user-defined.  It takes a word and returns True if it is
    spelled correctly and false if not. There are robust spell check libraries
    for python like woosh or pyenchant.  I have already written a naive
    spell checker in the pysle.praattools library.

    checkFunction: should return True if a word is spelled correctly and
                   False otherwise
    """
    punctuationList = [
        "_",
        ",",
        "'",
        '"',
        "!",
        "?",
        ".",
        ";",
    ]

    tg = tg.new()
    tier = tg.tierDict[targetTierName]

    mispelledEntryList = []
    for start, end, label in tier.entryList:

        # Remove punctuation
        for char in punctuationList:
            label = label.replace(char, "")

        wordList = label.split()
        mispelledList = []
        for word in wordList:
            if not checkFunction(word):
                mispelledList.append(word)

        if len(mispelledList) > 0:
            mispelledTxt = ", ".join(mispelledList)
            mispelledEntryList.append(Interval(start, end, mispelledTxt))

            if printEntries is True:
                print((start, end, mispelledTxt))

    tier = textgrid.IntervalTier(
        newTierName, mispelledEntryList, tg.minTimestamp, tg.maxTimestamp
    )
    tg.addTier(tier)

    return tg


def splitTierEntries(
    tg: textgrid.Textgrid,
    sourceTierName: str,
    targetTierName: str,
    startT: float = None,
    endT: float = None,
) -> textgrid.Textgrid:
    """
    Split each entry in a tier by space

    The split entries will be placed on a new tier.  The split entries
    are equally allocated a subsegment of the interval occupied by the
    source tier.  e.g. [(63, 66, 'the blue cat'), ] would become
    [(63, 64, 'the'), (64, 65, 'blue'), (65, 66, 'cat'), ]

    This could be used to decompose utterances into words or, with pysle,
    words into phones.
    """
    minT = tg.minTimestamp
    maxT = tg.maxTimestamp

    sourceTier = tg.tierDict[sourceTierName]
    targetTier = None

    # Examine a subset of the source tier?
    if startT is not None or endT is not None:
        if startT is None:
            startT = minT
        if endT is None:
            endT = maxT

        sourceTier = sourceTier.crop(startT, endT, "truncated", False)

        if targetTierName in tg.tierNameList:
            targetTier = tg.tierDict[targetTierName]
            targetTier = targetTier.eraseRegion(startT, endT, "truncate", False)

    # Split the entries in the source tier
    newEntryList = []
    for start, end, label in sourceTier.entryList:
        labelList = label.split()
        intervalLength = (end - start) / float(len(labelList))

        newSubEntryList = [
            Interval(
                start + intervalLength * i, start + intervalLength * (i + 1), label
            )
            for i, label in enumerate(labelList)
        ]
        newEntryList.extend(newSubEntryList)

    # Create a new tier
    if targetTier is None:
        targetTier = textgrid.IntervalTier(targetTierName, newEntryList, minT, maxT)

    # Or insert new entries into existing target tier
    else:

        for entry in newEntryList:
            targetTier.insertEntry(entry, constants.IntervalCollision.ERROR)

    # Insert the tier into the textgrid
    if targetTierName in tg.tierNameList:
        tg.removeTier(targetTierName)
    tg.addTier(targetTier)

    return tg


def tgBoundariesToZeroCrossings(
    tg: textgrid.Textgrid,
    wavObj: audio.WavObj,
    adjustPointTiers: bool = True,
    adjustIntervalTiers: bool = True,
) -> textgrid.Textgrid:
    """
    Makes all textgrid interval boundaries fall on pressure wave zero crossings

    adjustPointTiers: if True, point tiers will be adjusted.
    adjustIntervalTiers: if True, interval tiers will be adjusted.
    """
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]

        newTier: textgrid_tier.TextgridTier
        if isinstance(tier, textgrid.PointTier):
            if adjustPointTiers is False:
                continue

            points = []
            for start, label in tier.entryList:
                newStart = wavObj.findNearestZeroCrossing(start)
                points.append(Point(newStart, label))
            newTier = tier.new(entryList=points)
        elif isinstance(tier, textgrid.IntervalTier):
            if adjustIntervalTiers is False:
                continue

            intervals = []
            for start, end, label in tier.entryList:
                newStart = wavObj.findNearestZeroCrossing(start)
                newStop = wavObj.findNearestZeroCrossing(end)
                intervals.append(Interval(newStart, newStop, label))
            newTier = tier.new(entryList=intervals)

        tg.replaceTier(tierName, newTier)

    return tg


def splitAudioOnTier(
    wavFN: str,
    tgFN: str,
    tierName: str,
    outputPath: str,
    outputTGFlag: bool = False,
    nameStyle: Optional[Literal["append", "append_no_i", "label"]] = None,
    noPartialIntervals: bool = False,
    silenceLabel: str = None,
) -> List[Tuple[float, float, str]]:
    """
    Outputs one subwav for each entry in the tier of a textgrid

    Args:
        wavnFN (str):
        tgFN (str):
        tierName (str):
        outputPath (str):
        outputTGFlag (bool): If True, outputs paired, cropped textgrids
            If is type str (a tier name), outputs a paired, cropped
            textgrid with only the specified tier
        nameStyle (str):
            - 'append': append interval label to output name
            - 'append_no_i': append label but not interval to output name
            - 'label': output name is the same as label
            - None: output name plus the interval number
        noPartialIntervals (bool): if True: intervals in non-target tiers that
            are not wholly contained by an interval in the target tier will not
            be included in the output textgrids
        silenceLabel (str): the label for silent regions.  If silences are
            unlabeled intervals (i.e. blank) then leave this alone.  If
            silences are labeled using praat's "annotate >> to silences"
            then this value should be "silences"
    """
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)

    def getValue(myBool) -> Literal["strict", "lax", "truncated"]:
        # This will make mypy happy
        if myBool:
            return constants.CropCollision.STRICT
        else:
            return constants.CropCollision.TRUNCATED

    mode: Final = getValue(noPartialIntervals)

    tg = textgrid.openTextgrid(tgFN, False)
    entryList = tg.tierDict[tierName].entryList

    if silenceLabel is not None:
        entryList = [entry for entry in entryList if entry.label != silenceLabel]

    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagnitude = int(math.floor(math.log10(len(entryList))))

    # We want one more zero in the output than the order of magnitude
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagnitude + 1)

    firstWarning = True

    # If we're using the 'label' namestyle for outputs, all of the
    # interval labels have to be unique, or wave files with those
    # labels as names, will be overwritten
    if nameStyle == NameStyle.LABEL:
        wordList = [interval.label for interval in entryList]
        multipleInstList = []
        for word in set(wordList):
            if wordList.count(word) > 1:
                multipleInstList.append(word)

        if len(multipleInstList) > 0:
            instListTxt = "\n".join(multipleInstList)
            print(
                f"Overwriting wave files in: {outputPath}\n"
                f"Intervals exist with the same name:\n{instListTxt}"
            )
            firstWarning = False

    # Output wave files
    outputFNList = []
    wavQObj = audio.WavQueryObj(wavFN)
    for i, entry in enumerate(entryList):
        start, end, label = entry

        # Resolve output name
        if nameStyle == NameStyle.APPEND_NO_I:
            outputName = f"{name}_{label}"
        elif nameStyle == NameStyle.LABEL:
            outputName = label
        else:
            outputName = outputTemplate % i
            if nameStyle == NameStyle.APPEND:
                outputName += f"_{label}"

        outputFNFullPath = join(outputPath, outputName + ".wav")

        if os.path.exists(outputFNFullPath) and firstWarning:
            print(
                f"Overwriting wave files in: {outputPath}\n"
                "Files existed before or intervals exist with "
                f"the same name:\n{outputName}"
            )

        frames = wavQObj.getFrames(start, end)
        wavQObj.outputModifiedWav(frames, outputFNFullPath)

        outputFNList.append((start, end, outputName + ".wav"))

        # Output the textgrid if requested
        if outputTGFlag is not False:
            subTG = tg.crop(start, end, mode, True)

            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNameList:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)

            subTG.save(
                join(outputPath, outputName + ".TextGrid"), "short_textgrid", True
            )

    return outputFNList


def alignBoundariesAcrossTiers(
    tgFN: str, maxDifference: float = 0.01
) -> textgrid.Textgrid:
    """
    Aligns boundaries or points in a textgrid that suffer from 'jitter'

    Often times, boundaries in different tiers are meant to line up.
    For example the boundary of the first phone in a word and the start
    of the word.  If manually annotated, however, those values might
    not be the same, even if they were intended to be the same.

    This script will force all boundaries within /maxDifference/ amount
    to be the same value.  The replacement value is either the majority
    value found within /maxDifference/ or, if no majority exists, than
    the value used in the search query.
    """
    tg = textgrid.openTextgrid(tgFN, False)

    for tierName in tg.tierNameList:
        altNameList = [tmpName for tmpName in tg.tierNameList if tmpName != tierName]

        tier = tg.tierDict[tierName]
        for entry in tier.entryList:
            # Interval tier left boundary or point tier point
            _findMisalignments(
                tg, entry[0], maxDifference, altNameList, tierName, entry, 0
            )

        # Interval tier right boundary
        if tier.tierType == textgrid.INTERVAL_TIER:
            for entry in tier.entryList:
                _findMisalignments(
                    tg, entry[1], maxDifference, altNameList, tierName, entry, 1
                )

    return tg


def _findMisalignments(
    tg: textgrid.Textgrid,
    timeV: float,
    maxDifference: float,
    tierNameList: List[str],
    tierName: str,
    entry: list,
    orderID: int,
) -> None:
    """
    This is just used by alignBoundariesAcrossTiers()
    """
    # Get the start time
    filterStartT = timeV - maxDifference
    if filterStartT < 0:
        filterStartT = 0

    # Get the end time
    filterStopT = timeV + maxDifference
    if filterStopT > tg.maxTimestamp:
        filterStopT = tg.maxTimestamp

    croppedTG = tg.crop(filterStartT, filterStopT, "lax", False)

    matchList = [(tierName, timeV, entry, orderID)]
    for subTierName in tierNameList:
        subCroppedTier = croppedTG.tierDict[subTierName]

        # For each item that exists in the search span, find the boundary
        # that lies in the search span
        for subCroppedEntry in subCroppedTier.entryList:

            if subCroppedTier.tierType == textgrid.INTERVAL_TIER:
                subStart, subEnd, _ = subCroppedEntry

                # Left boundary?
                leftMatchVal = None
                if subStart >= filterStartT and subStart <= filterStopT:
                    leftMatchVal = subStart

                # Right boundary?
                rightMatchVal = None
                if subEnd >= filterStartT and subEnd <= filterStopT:
                    rightMatchVal = subEnd

                if (
                    leftMatchVal is not None and rightMatchVal is not None
                ):  # This shouldn't happen
                    raise errors.UnexpectedError(
                        "There should be at most one matching boundary."
                    )

                # Set the matching boundary info
                if leftMatchVal is not None:
                    matchVal = leftMatchVal
                    subOrderID = 0
                else:
                    matchVal = rightMatchVal
                    subOrderID = 1

                # Match value could be none if, for an interval tier,
                # no boundary sits inside the search span (the search span
                # is wholly inside the interval)
                if matchVal is None:
                    continue

            elif subCroppedTier.tierType == constants.POINT_TIER:
                subStart, _ = subCroppedEntry
                if subStart >= filterStartT and subStart <= filterStopT:
                    matchVal = subStart
                    subOrderID = 0

            matchList.append((subTierName, matchVal, subCroppedEntry, subOrderID))

    # Find the number of different values that are almost the same
    valList = [row[1] for row in matchList]
    valUniqueList = []
    for val in valList:
        if val not in valUniqueList:
            valUniqueList.append(val)

    # If they're all the same, there is nothing to do
    # If some are different, take the most common value (or else the first
    # one) and set all similar times to that value
    if len(valUniqueList) > 1:
        countList = [valList.count(val) for val in valUniqueList]
        bestVal = valUniqueList[countList.index(max(countList))]
        if bestVal is None:  # When can this happen?
            raise errors.UnexpectedError("Could not find the optimal value")
        for tierName, _, oldEntry, orderID in matchList:

            newEntry = list(copy.deepcopy(oldEntry))
            newEntry[orderID] = bestVal
            castNewEntry = tg.tierDict[tierName].entryType(*newEntry)

            tg.tierDict[tierName].deleteEntry(oldEntry)
            tg.tierDict[tierName].entryList.append(castNewEntry)
            tg.tierDict[tierName].entryList.sort()
