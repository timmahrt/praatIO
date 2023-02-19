"""
Common/generic scripts or utilities that extend the functionality of praatio

see **examples/correct_misaligned_tiers.py**, **examples/delete_vowels.py**,
**examples/extract_subwavs.py**, **examples/splice_example.py**.
"""

import os
from os.path import join
import math
from typing import Callable, List, Tuple

from typing_extensions import Literal, Final

from praatio import textgrid
from praatio import audio
from praatio.utilities import utils
from praatio.data_classes import textgrid_tier
from praatio.utilities import constants
from praatio.utilities.constants import Point, Interval, NameStyle
from praatio.utilities import errors


def _shiftTimes(
    tg: textgrid.Textgrid, timeV: float, newTimeV: float
) -> textgrid.Textgrid:
    """Change all instances of timeV in the textgrid to newTimeV

    These are meant to be small changes.  No checks are done to see
    if the new interval steps on other intervals
    """
    tg = tg.new()
    for tier in tg.tiers:
        if isinstance(tier, textgrid.IntervalTier):
            entries = [
                entry
                for entry in tier.entries
                if entry[0] == timeV or entry[1] == timeV
            ]
            insertEntries = []
            for entry in entries:
                if entry[0] == timeV:
                    newStart, newStop = newTimeV, entry[1]
                elif entry[1] == timeV:
                    newStart, newStop = entry[0], newTimeV
                tier.deleteEntry(entry)
                insertEntries.append((newStart, newStop, entry[2]))

            for entry in insertEntries:
                tier.insertEntry(entry)

        elif isinstance(tier, textgrid.PointTier):
            entries = [entry for entry in tier.entries if entry[0] == timeV]
            for entry in entries:
                tier.deleteEntry(entry)
                tier.insertEntry(Point(newTimeV, entry[1]))

    return tg


def audioSplice(
    audioObj: audio.Wav,
    spliceSegment: audio.Wav,
    tg: textgrid.Textgrid,
    tierName: str,
    newLabel: str,
    insertStart: float,
    insertStop: float = None,
    alignToZeroCrossing: bool = True,
) -> Tuple[audio.Wav, textgrid.Textgrid]:
    """Splices a segment into an audio file and corresponding textgrid

    Args:
        audioObj: the audio to splice into
        spliceSegment: the audio segment that will be placed into a
            larger audio file
        tg: the textgrid to splice into
        tierName: the name of the tier that will receive the new label
        newLabel: the label for the splice interval on the tier with
            name tierName
        insertStart: the time to insert the splice
        insertStop: if not None, will erase the region between
            sourceSpStart and sourceSpEnd.  (In practice this means audioSplice
            removes one segment and inserts another in its place)
        alignToZeroCrossing: if True, moves all involved times to the nearest
            zero crossing in the audio.  Generally results
            in better sounding output

    Returns:
        [Wav, Textgrid]
    """

    retTG = tg.new()

    # Ensure all time points involved in splicing fall on zero crossings
    if alignToZeroCrossing is True:

        # Cut the splice segment to zero crossings
        spliceDuration = spliceSegment.duration
        spliceZeroStart = spliceSegment.findNearestZeroCrossing(0)
        spliceZeroEnd = spliceSegment.findNearestZeroCrossing(spliceDuration)
        spliceSegment = spliceSegment.getSubwav(spliceZeroStart, spliceZeroEnd)

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
    audioObj.insert(insertTime, spliceSegment.frames)

    # Insert a blank region into the textgrid on all tiers
    targetDuration = spliceSegment.duration
    retTG = retTG.insertSpace(insertTime, targetDuration, "stretch")

    # Insert the splice entry into the target tier
    newEntry = (insertTime, insertTime + targetDuration, newLabel)
    retTG.getTier(tierName).insertEntry(newEntry)

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
    """Spell checks words in a textgrid

    Entries can contain one or more words, separated by whitespace.
    If a mispelling is found, it is noted in a special tier and optionally
    printed to the screen.

    checkFunction is user-defined.  It takes a word and returns True if it is
    spelled correctly and false if not. There are robust spell check libraries
    for python like woosh or pyenchant.  I have already written a naive
    spell checker in the pysle.praattools library.

    Args:
        checkFunction: should return True if a word is spelled correctly and
            False otherwise

    Raises:
        TierNameExistsError: newTierName exists in the textgrid
    """
    punctuationList = [
        "-",
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
    tier = tg.getTier(targetTierName)

    mispelledEntries = []
    for start, end, label in tier.entries:

        # Remove punctuation
        for char in punctuationList:
            label = label.replace(char, " ")

        wordList = label.split()
        mispelledList = []
        for word in wordList:
            if not checkFunction(word):
                mispelledList.append(word)

        if len(mispelledList) > 0:
            mispelledTxt = ", ".join(mispelledList)
            mispelledEntries.append(Interval(start, end, mispelledTxt))

            if printEntries is True:
                print((start, end, mispelledTxt))

    tier = textgrid.IntervalTier(
        newTierName, mispelledEntries, tg.minTimestamp, tg.maxTimestamp
    )
    tg.addTier(tier)

    return tg


def splitTierEntries(
    tg: textgrid.Textgrid, sourceTierName: str, targetTierName: str
) -> textgrid.Textgrid:
    """Split each entry in a tier by space

    The split entries will be placed on a new tier.  The split entries
    are equally allocated a subsegment of the interval occupied by the
    source tier.  e.g. [(63, 66, 'the blue cat'), ] would become
    [(63, 64, 'the'), (64, 65, 'blue'), (65, 66, 'cat'), ]

    This could be used to decompose utterances into words or, with pysle,
    words into phones.

    Returns:
        A modified version of the input textgrid

    Raises:
        CollisionError: If targetTierName exists in the textgrid, this will attempt
                        to write the new content into it; if any of the new intervals
                        overlap with existing intervals, this will fail.
    """
    minT = tg.minTimestamp
    maxT = tg.maxTimestamp

    sourceTier = tg.getTier(sourceTierName)
    targetTier = None
    if targetTierName in tg.tierNames:
        targetTier = tg.getTier(targetTierName)

    # Split the entries in the source tier
    newEntries = []
    for start, end, label in sourceTier.entries:
        labelList = label.split()
        intervalLength = (end - start) / float(len(labelList))

        newSubEntries = [
            Interval(
                start + intervalLength * i, start + intervalLength * (i + 1), label
            )
            for i, label in enumerate(labelList)
        ]
        newEntries.extend(newSubEntries)

    # Create a new tier
    if targetTier is None:
        targetTier = textgrid.IntervalTier(targetTierName, newEntries, minT, maxT)

    # Or insert new entries into existing target tier
    else:

        for entry in newEntries:
            targetTier.insertEntry(entry, constants.IntervalCollision.ERROR)

    # Insert the tier into the textgrid
    if targetTierName in tg.tierNames:
        tg.removeTier(targetTierName)
    tg.addTier(targetTier)

    return tg


def tgBoundariesToZeroCrossings(
    tg: textgrid.Textgrid,
    wav: audio.Wav,
    adjustPointTiers: bool = True,
    adjustIntervalTiers: bool = True,
) -> textgrid.Textgrid:
    """Makes all textgrid interval boundaries fall on pressure wave zero crossings

    adjustPointTiers: if True, point tiers will be adjusted.
    adjustIntervalTiers: if True, interval tiers will be adjusted.
    """
    for tier in tg.tiers:
        newTier: textgrid_tier.TextgridTier
        if isinstance(tier, textgrid.PointTier):
            if adjustPointTiers is False:
                continue

            points = []
            for start, label in tier.entries:
                newStart = wav.findNearestZeroCrossing(start)
                points.append(Point(newStart, label))
            newTier = tier.new(entries=points)
        elif isinstance(tier, textgrid.IntervalTier):
            if adjustIntervalTiers is False:
                continue

            intervals = []
            for start, end, label in tier.entries:
                newStart = wav.findNearestZeroCrossing(start)
                newStop = wav.findNearestZeroCrossing(end)
                intervals.append(Interval(newStart, newStop, label))
            newTier = tier.new(entries=intervals)

        tg.replaceTier(tier.name, newTier)

    return tg


def splitAudioOnTier(
    wavFN: str,
    tgFN: str,
    tierName: str,
    outputPath: str,
    outputTGFlag: bool = False,
    nameStyle: Literal[
        "name_and_i_and_label", "name_and_label", "name_and_i", "label"
    ] = "name_and_i",
    allowPartialIntervals: bool = True,
    silenceLabel: str = None,
) -> List[Tuple[float, float, str]]:
    """Outputs one subwav for each entry in the tier of a textgrid

    Args:
        wavnFN:
        tgFN:
        tierName:
        outputPath:
        outputTGFlag: If True, outputs paired, cropped textgrids
            If is type str (a tier name), outputs a paired, cropped
            textgrid with only the specified tier
        nameStyle:
            - 'name_and_i_and_label': append interval label to output name
            - 'name_and_label': append label but not interval to output name
            - 'name_and_i': output name plus the interval number
            - 'label': output name is the same as label
        allowPartialIntervals: if False: intervals in non-target tiers that
            are not wholly contained by an interval in the target tier will not
            be included in the output textgrids
        silenceLabel: the label for silent regions.  If silences are
            unlabeled intervals (i.e. blank) then leave this alone.  If
            silences are labeled using praat's "annotate >> to silences"
            then this value should be "silences"
    """
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)

    utils.validateOption("nameStyle", nameStyle, NameStyle)

    mode: Final = _getMode(allowPartialIntervals)

    tg = textgrid.openTextgrid(tgFN, False)
    entries = tg.getTier(tierName).entries

    # Build the output name template
    outputNameBase = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagnitude = int(math.floor(math.log10(len(entries))))

    # We want one more zero in the output than the order of magnitude
    outputTemplate = "%s_%%0%dd" % (outputNameBase, orderOfMagnitude + 1)
    nameStyleToNameGenerator = {
        "name_and_i_and_label": lambda _name, label, i: f"{outputTemplate % i}_{label}",
        "name_and_label": lambda name, label, _i: f"{name}_{label}",
        "name_and_i": lambda _name, _label, i: f"{outputTemplate % i}",
        "label": lambda _name, label, _i: label,
    }
    generateName = nameStyleToNameGenerator[nameStyle]

    if silenceLabel is not None:
        entries = [entry for entry in entries if entry.label != silenceLabel]

    logger = utils.TogglableLogger(autoDisable=True)
    _validateEntriesForWriting(nameStyle, entries, logger, outputPath)
    logger.autoDisable = False

    # Output wave files
    outputFNList = []
    wavQObj = audio.QueryWav(wavFN)
    for i, entry in enumerate(entries):
        start, end, label = entry

        outputName = generateName(outputNameBase, label, i)
        outputFNFullPath = join(outputPath, outputName + ".wav")

        if os.path.exists(outputFNFullPath):
            logger.write(
                f"Overwriting wave files in: {outputPath}\n"
                "Files existed before or intervals exist with "
                f"the same name:\n{outputName}"
            )

        frames = wavQObj.getFrames(start, end)
        wavQObj.outputFrames(frames, outputFNFullPath)

        outputFNList.append((start, end, outputName + ".wav"))

        # Output the textgrid if requested
        if outputTGFlag is not False:
            subTG = tg.crop(start, end, mode, True)

            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNames:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)

            subTG.save(
                join(outputPath, outputName + ".TextGrid"), "short_textgrid", True
            )

    return outputFNList


def _getMode(allowPartialIntervals: bool) -> Literal["strict", "lax", "truncated"]:
    # This helper function is just to make mypy happy
    if allowPartialIntervals:
        return constants.CropCollision.TRUNCATED
    else:
        return constants.CropCollision.STRICT


def _validateEntriesForWriting(nameStyle, entries, logger, outputPath):
    # If we're using the 'label' namestyle for outputs, all of the
    # interval labels have to be unique, or wave files with those
    # labels as names, will be overwritten
    if nameStyle == NameStyle.LABEL:
        wordList = [interval.label for interval in entries]
        multipleInstList = []
        for word in utils.getUnique(wordList):
            if wordList.count(word) > 1:
                multipleInstList.append(word)

        if len(multipleInstList) > 0:
            instListTxt = "\n".join(multipleInstList)
            logger.write(
                f"Overwriting wave files in: {outputPath}\n"
                f"Intervals exist with the same name:\n{instListTxt}"
            )


# TODO: Remove this method in the next major version
#       Migrate to using the new Textgridtier.dejitter()
def alignBoundariesAcrossTiers(
    tg: textgrid.Textgrid, tierName: str, maxDifference: float = 0.005
) -> textgrid.Textgrid:
    """Aligns boundaries or points in a textgrid that suffer from 'jitter'

    Often times, boundaries in different tiers are meant to line up.
    For example the boundary of the first phone in a word and the start
    of the word.  If manually annotated, however, those values might
    not be the same, even if they were intended to be the same.

    This script will force all boundaries within /maxDifference/ amount
    to be the same value.  The replacement value is either the majority
    value found within /maxDifference/ or, if no majority exists, than
    the value used in the search query.

    Args:
        tg: the textgrid to operate on
        tierName: the name of the reference tier to compare other tiers against
        maxDifference: any boundaries that differ less this amount compared
                       to boundaries in the reference tier will be adjusted

    Returns:
        the provided textgrid with aligned boundaries

    Raises:
        ArgumentError: The provided maxDifference is larger than the smallest difference in
                       the tier to be used for comparisons, which could lead to strange results.
                       In such a case, choose a smaller maxDifference.
    """
    referenceTier = tg.getTier(tierName)
    times = referenceTier.timestamps

    for time, nextTime in zip(times[1::], times[2::]):
        if nextTime - time < maxDifference:
            raise errors.ArgumentError(
                "The provided maxDifference is larger than the smallest difference in"
                "the tier used for comparison, which could lead to strange results."
                "Please choose a smaller maxDifference.\n"
                f"Max difference: {maxDifference}\n"
                f"found difference {nextTime - time} for times {time} and {nextTime}"
            )

    for tier in tg.tiers:
        if tier.name == tierName:
            continue

        tier = tier.dejitter(referenceTier, maxDifference)
        tg.replaceTier(tier.name, tier)

    return tg
