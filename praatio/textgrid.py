"""
Functions for reading/writing/manipulating textgrid files.

This file contains the main data structures for representing Textgrid data:
Textgrid, IntervalTier, and PointTier

A Textgrid is a container for multiple annotation tiers.  Tiers can contain
either interval data (IntervalTier) or point data (PointTier).
Tiers in a Textgrid are ordered and must contain a unique name.

openTextgrid() can be used to open a textgrid file.
Textgrid.save() can be used to save a Textgrid object to a file.

see the **examples/** directory for lots of examples using tgio.py
"""

import re
import copy
import io
from collections import namedtuple

from praatio.utilities import utils
from praatio.utilities import myMath

INTERVAL_TIER = "IntervalTier"
POINT_TIER = "TextTier"

Interval = namedtuple("Interval", ["start", "end", "label"])  # interval entry
Point = namedtuple("Point", ["time", "label"])  # point entry


def intervalOverlapCheck(
    interval, cmprInterval, percentThreshold=0, timeThreshold=0, boundaryInclusive=False
):
    """
    Checks whether two intervals overlap

    Args:
        interval (Interval):
        cmprInterval (Interval):
        percentThreshold (float): if percentThreshold is greater than 0, then
            if the intervals overlap, they must overlap by at least this threshold
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

    # Is the overlap more than a certain threshold?
    timeOverlapFlag = False
    if timeThreshold > 0 and overlapFlag:
        timeOverlapFlag = overlapTime > timeThreshold

    overlapFlag = (
        overlapFlag or boundaryOverlapFlag or percentOverlapFlag or timeOverlapFlag
    )

    return overlapFlag


class TextgridCollisionException(Exception):
    def __init__(self, tierName, insertInterval, collisionList):
        super(TextgridCollisionException, self).__init__()
        self.tierName = tierName
        self.insertInterval = insertInterval
        self.collisionList = collisionList

    def __str__(self):
        dataTuple = (str(self.insertInterval), self.tierName, str(self.collisionList))
        return (
            "Attempted to insert interval %s into tier %s of textgrid"
            + "but overlapping entries %s already exist" % dataTuple
        )


class TimelessTextgridTierException(Exception):
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


class BadIntervalError(Exception):
    def __init__(self, start, stop, label):
        super(BadIntervalError, self).__init__()
        self.start = start
        self.stop = stop
        self.label = label

    def __str__(self):
        dataTuple = (self.start, self.stop, self.label)
        return (
            "Problem with interval--could not create textgrid "
            + "(%s,%s,%s)" % dataTuple
        )


class BadFormatException(Exception):
    def __init__(self, selectedFormat, validFormatOptions):
        super(BadFormatException, self).__init__()
        self.selectedFormat = selectedFormat
        self.validFormatOptions = validFormatOptions

    def __str__(self):
        dataTuple = (self.selectedFormat, ", ".join(self.validFormatOptions))
        return (
            "Problem with format.  Received %s but format must be one of %s" % dataTuple
        )


class TextgridTier(object):

    tierType = None
    entryType = Interval

    def __init__(self, name, entryList, minT, maxT, pairedWav=None):
        """See PointTier or IntervalTier"""
        entryList.sort()

        self.name = name
        self.entryList = entryList
        self.minTimestamp = minT
        self.maxTimestamp = maxT

    def __eq__(self, other):
        isEqual = True
        isEqual &= self.name == other.name
        isEqual &= myMath.isclose(self.minTimestamp, other.minTimestamp)
        isEqual &= myMath.isclose(self.maxTimestamp, other.maxTimestamp)
        isEqual &= len(self.entryList) == len(self.entryList)

        if isEqual:
            for selfEntry, otherEntry in zip(self.entryList, other.entryList):
                for selfSubEntry, otherSubEntry in zip(selfEntry, otherEntry):
                    try:
                        isEqual &= myMath.isclose(selfSubEntry, otherSubEntry)
                    except TypeError:
                        isEqual &= selfSubEntry == otherSubEntry

        return isEqual

    def appendTier(self, tier):
        """
        Append a tier to the end of this one.

        This tier's maxtimestamp will be lengthened by the amount in the passed in tier.
        """

        minTime = self.minTimestamp
        if tier.minTimestamp < minTime:
            minTime = tier.minTimestamp

        maxTime = self.maxTimestamp + tier.maxTimestamp

        appendTier = tier.editTimestamps(self.maxTimestamp, allowOvershoot=True)

        assert self.tierType == tier.tierType

        entryList = self.entryList + appendTier.entryList
        entryList.sort()

        return self.new(
            self.name, entryList, minTimestamp=minTime, maxTimestamp=maxTime
        )

    def deleteEntry(self, entry):
        """Removes an entry from the entryList"""
        self.entryList.pop(self.entryList.index(entry))

    def find(self, matchLabel, substrMatchFlag=False, usingRE=False):
        """
        Returns the index of all intervals that match the given label

        Args:
            matchLabel (str): the label to search for
            substrMatchFlag (bool): if True, match any label containing matchLabel. if False, label must be the same as matchLabel.
            usingRE (bool): if True, matchLabel is interpreted as a regular expression

        Returns:
            List: A list of indicies
        """
        returnList = []
        if usingRE is True:
            for i, entry in enumerate(self.entryList):
                matchList = re.findall(matchLabel, entry[-1], re.I)
                if matchList != []:
                    returnList.append(i)
        else:
            for i, entry in enumerate(self.entryList):
                if not substrMatchFlag:
                    if entry[-1] == matchLabel:
                        returnList.append(i)
                else:
                    if matchLabel in entry[-1]:
                        returnList.append(i)

        return returnList

    def getAsText(self):
        """
        Prints each entry in the tier on a separate line w/ timing info

        TODO: Delete this?  It was being used in writing shortform textgrids
              but is not anymore
        """
        text = ""
        text += '"%s"\n' % self.tierType
        text += '"%s"\n' % self.name
        text += "%s\n%s\n%s\n" % (
            myMath.numToStr(self.minTimestamp),
            myMath.numToStr(self.maxTimestamp),
            len(self.entryList),
        )

        for entry in self.entryList:
            entry = [myMath.numToStr(val) for val in entry[:-1]] + [
                '"%s"' % entry[-1],
            ]
            try:
                unicode
            except NameError:
                unicodeFunc = str
            else:
                unicodeFunc = unicode

            text += "\n".join([unicodeFunc(val) for val in entry]) + "\n"

        return text

    def new(
        self,
        name=None,
        entryList=None,
        minTimestamp=None,
        maxTimestamp=None,
        pairedWav=None,
    ):
        """Make a new tier derived from the current one"""
        if name is None:
            name = self.name
        if entryList is None:
            entryList = copy.deepcopy(self.entryList)
            entryList = [
                self.entryType(*entry) if isinstance(entry, tuple) else entry
                for entry in entryList
            ]
        if minTimestamp is None:
            minTimestamp = self.minTimestamp
        if maxTimestamp is None and pairedWav is None:
            maxTimestamp = self.maxTimestamp
        return type(self)(name, entryList, minTimestamp, maxTimestamp, pairedWav)

    def sort(self):
        """Sorts the entries in the entryList"""
        # A list containing tuples and lists will be sorted with tuples
        # first and then lists.  To correctly sort, we need to make
        # sure that all data structures inside the entry list are
        # of the same data type.  The entry list is sorted whenever
        # the entry list is modified, so this is probably the best
        # place to enforce the data type
        self.entryList = [
            entry if isinstance(entry, self.entryType) else self.entryType(*entry)
            for entry in self.entryList
        ]
        self.entryList.sort()

    def union(self, tier):
        """
        The given tier is set unioned to this tier.

        All entries in the given tier are added to the current tier.
        Overlapping entries are merged.
        """
        retTier = self.new()

        for entry in tier.entryList:
            retTier.insertEntry(entry, False, collisionCode="merge")

        retTier.sort()

        return retTier


class PointTier(TextgridTier):

    tierType = POINT_TIER
    entryType = Point

    def __init__(self, name, entryList, minT=None, maxT=None, pairedWav=None):
        """
        A point tier is for annotating instaneous events

        The entryList is of the form:
        [(timeVal1, label1), (timeVal2, label2), ]

        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('peak point here') or numerical data e.g. (pitch values
        like '132'))
        """

        entryList = [Point(float(time), label) for time, label in entryList]

        # Determine the min and max timestamps
        timeList = [time for time, label in entryList]
        if minT is not None:
            timeList.append(float(minT))
        if maxT is not None:
            timeList.append(float(maxT))

        if maxT is None and pairedWav is not None:
            maxT = utils.getWavDuration(pairedWav)

        try:
            minT = min(timeList)
            maxT = max(timeList)
        except ValueError:
            raise TimelessTextgridTierException()

        super(PointTier, self).__init__(name, entryList, minT, maxT)

    def crop(self, cropStart, cropEnd, mode=None, rebaseToZero=True):
        """
        Creates a new tier containing all entries inside the new interval

        Args:
            cropStart (float):
            cropEnd (float):
            mode (str): Mode is ignored.  This parameter is kept for
                compatibility with IntervalTier.crop()
            rebaseToZero (bool): if True, all entries will have their
                timestamps subtracted by *cropStart*.

        Returns:
            PointTier: the modified version of the current tier
        """
        newEntryList = []

        for entry in self.entryList:
            timestamp = entry[0]

            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntryList.append(entry)

        if rebaseToZero is True:
            newEntryList = [(timeV - cropStart, label) for timeV, label in newEntryList]
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return PointTier(self.name, newEntryList, minT, maxT)

    def editTimestamps(self, offset, allowOvershoot=False):
        """
        Modifies all timestamps by a constant amount

        Args:
            offset (float):
            allowOvershoot (bool): if True, an interval can go beyond
                the bounds of the textgrid

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntryList = []
        for timestamp, label in self.entryList:

            newTimestamp = timestamp + offset
            if not allowOvershoot:
                assert newTimestamp > self.minTimestamp
                assert newTimestamp <= self.maxTimestamp

            if newTimestamp < 0:
                continue

            newEntryList.append((newTimestamp, label))

        # Determine new min and max timestamps
        timeList = [float(subList[0]) for subList in newEntryList]
        newMin = min(timeList)
        newMax = max(timeList)

        if newMin > self.minTimestamp:
            newMin = self.minTimestamp

        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp

        return PointTier(self.name, newEntryList, newMin, newMax)

    def getValuesAtPoints(self, dataTupleList, fuzzyMatching=False):
        """
        Get the values that occur at points in the point tier

        Args:
            dataTupleList (list):
            fuzzyMatching (bool): if True, if there is not a feature value
                at a point, the nearest feature value will be taken.

        Returns:
            List

        The procedure assumes that all data is ordered in time.
        dataTupleList should be in the form
        [(t1, v1a, v1b, ..), (t2, v2a, v2b, ..), ..]

        The procedure makes one pass through dataTupleList and one
        pass through self.entryList.  If the data is not sequentially
        ordered, the incorrect response will be returned.
        """

        i = 0
        retList = []

        sortedDataTupleList = dataTupleList.sorted()
        for timestamp, label in self.entryList:
            retTuple = utils.getValueAtTime(
                timestamp, sortedDataTupleList, fuzzyMatching=fuzzyMatching, startI=i
            )
            retTime, retVal, i = retTuple
            retList.append((retTime, label, retVal))

        return retList

    def eraseRegion(self, start, stop, collisionCode=None, doShrink=True):
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float): the start of the deletion interval
            stop (float): the end of the deletion interval
            collisionCode (str): Ignored for the moment (added for compatibility with eraseRegion() for Interval Tiers)
            doShrink (bool): if True, moves leftward by (/stop/ - /start/) all points to the right of /stop/

        Returns:
            PointTier: the modified version of the current tier
        """

        newTier = self.new()
        croppedTier = newTier.crop(start, stop, "truncated", False)
        matchList = croppedTier.entryList

        if len(matchList) == 0:
            pass
        else:

            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for tmpEntry in matchList[::-1]:
                newTier.deleteEntry(tmpEntry)

        if doShrink is True:
            newEntryList = []
            diff = stop - start
            for timestamp, label in newTier.entryList:
                if timestamp < start:
                    newEntryList.append((timestamp, label))
                elif timestamp > stop:
                    newEntryList.append((timestamp - diff, label))

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList, maxTimestamp=newMax)

        return newTier

    def insertEntry(self, entry, warnFlag=True, collisionCode=None):
        """
        inserts an interval into the tier

        Args:
            entry (tuple|Point): the entry to insert
            warnFlag (bool): see below for details
            collisionCode (str): determines the behavior if intervals exist in
                the insertion area. One of ('replace', 'merge', or None)
                - 'replace', existing items will be removed
                - 'merge', inserting item will be fused with existing items
                - None or any other value will thrown TextgridCollisionException

        Returns:
            None

        If warnFlag is True and collisionCode is not None, the user is notified
        of each collision
        """
        timestamp, label = entry

        if not isinstance(entry, Point):
            entry = Point(timestamp, label)

        matchList = []
        i = None
        for i, searchEntry in self.entryList:
            if searchEntry[0] == entry[0]:
                matchList.append(searchEntry)
                break

        if len(matchList) == 0:
            self.entryList.append(entry)

        elif collisionCode.lower() == "replace":
            self.deleteEntry(self.entryList[i])
            self.entryList.append(entry)

        elif collisionCode.lower() == "merge":
            oldEntry = self.entryList[i]
            newEntry = Point(timestamp, "-".join([oldEntry[-1], label]))
            self.deleteEntry(self.entryList[i])
            self.entryList.append(newEntry)

        else:
            raise TextgridCollisionException(self.name, entry, matchList)

        self.sort()

        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(entry), str(matchList), self.name)))

    def insertSpace(self, start, duration, collisionCode=None):
        """
        Inserts a region into the tier

        Args:
            start (float): the start time to insert a space at
            duration (float): the duration of the space to insert
            collisionCode (str): Ignored for the moment (added for compatibility with insertSpace() for Interval Tiers)

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntryList = []
        for entry in self.entryList:
            if entry[0] <= start:
                newEntryList.append(entry)
            elif entry[0] > start:
                newEntryList.append((entry[0] + duration, entry[1]))

        newTier = self.new(
            entryList=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier


class IntervalTier(TextgridTier):

    tierType = INTERVAL_TIER
    entryType = Interval

    def __init__(self, name, entryList, minT=None, maxT=None, pairedWav=None):
        """
        An interval tier is for annotating events that have duration

        The entryList is of the form:
        [(startTime1, endTime1, label1), (startTime2, endTime2, label2), ]

        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('erase this region') or numerical data e.g. (average pitch
        values like '132'))
        """
        entryList = [
            (float(start), float(stop), label) for start, stop, label in entryList
        ]

        if minT is not None:
            minT = float(minT)
        if maxT is not None:
            maxT = float(maxT)

        if maxT is None and pairedWav is not None:
            maxT = utils.getWavDuration(pairedWav)

        # Prevent poorly-formed textgrids from being created
        for entry in entryList:
            if entry[0] >= entry[1]:
                fmtStr = "Anomaly: startTime=%f, stopTime=%f, label=%s"
                print((fmtStr % (entry[0], entry[1], entry[2])))
            assert entry[0] < entry[1]

        # Remove whitespace
        tmpEntryList = []
        for start, stop, label in entryList:
            tmpEntryList.append(Interval(start, stop, label.strip()))
        entryList = tmpEntryList

        # Determine the minimum and maximum timestampes
        minTimeList = [subList[0] for subList in entryList]
        maxTimeList = [subList[1] for subList in entryList]

        if minT is not None:
            minTimeList.append(minT)
        if maxT is not None:
            maxTimeList.append(maxT)

        try:
            minT = min(minTimeList)
            maxT = max(maxTimeList)
        except ValueError:
            raise TimelessTextgridTierException()

        super(IntervalTier, self).__init__(name, entryList, minT, maxT)

    def crop(self, cropStart, cropEnd, mode, rebaseToZero):
        """
        Creates a new tier with all entries that fit inside the new interval

        Args:
            cropStart (float):
            cropEnd (float):
            mode (string): one of ['strict', 'lax', or 'truncated']
                - 'strict', only intervals wholly contained by the crop
                    interval will be kept
                - 'lax', partially contained intervals will be kept
                - 'truncated', partially contained intervals will be
                    truncated to fit within the crop region.
            rebaseToZero (bool): if True, the cropped textgrid values
                will be subtracted by the cropStart

        Returns:
            IntervalTier: the modified version of the current tier
        """

        assert mode in ["strict", "lax", "truncated"]

        # Debugging variables
        cutTStart = 0
        cutTWithin = 0
        cutTEnd = 0
        firstIntervalKeptProportion = 0
        lastIntervalKeptProportion = 0

        newEntryList = []
        for entry in self.entryList:
            matchedEntry = None

            intervalStart = entry[0]
            intervalEnd = entry[1]
            intervalLabel = entry[2]

            # Don't need to investigate if the interval is before or after
            # the crop region
            if intervalEnd <= cropStart or intervalStart >= cropEnd:
                continue

            # Determine if the current subEntry is wholly contained
            # within the superEntry
            if intervalStart >= cropStart and intervalEnd <= cropEnd:
                matchedEntry = entry

            # If it is only partially contained within the superEntry AND
            # inclusion is 'lax', include it anyways
            elif mode == "lax" and (
                intervalStart >= cropStart or intervalEnd <= cropEnd
            ):
                matchedEntry = entry

            # If not strict, include partial tiers on the edges
            # -- regardless, record how much information was lost
            #        - for strict=True, the total time of the cut interval
            #        - for strict=False, the portion of the interval that lies
            #            outside the new interval

            # The current interval stradles the end of the new interval
            elif intervalStart >= cropStart and intervalEnd > cropEnd:
                cutTEnd = intervalEnd - cropEnd
                lastIntervalKeptProportion = (cropEnd - intervalStart) / (
                    intervalEnd - intervalStart
                )

                if mode == "truncated":
                    matchedEntry = (intervalStart, cropEnd, intervalLabel)

                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval stradles the start of the new interval
            elif intervalStart < cropStart and intervalEnd <= cropEnd:
                cutTStart = cropStart - intervalStart
                firstIntervalKeptProportion = (intervalEnd - cropStart) / (
                    intervalEnd - intervalStart
                )
                if mode == "truncated":
                    matchedEntry = (cropStart, intervalEnd, intervalLabel)
                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval contains the new interval completely
            elif intervalStart <= cropStart and intervalEnd >= cropEnd:

                if mode == "lax":
                    matchedEntry = entry
                elif mode == "truncated":
                    matchedEntry = (cropStart, cropEnd, intervalLabel)
                else:
                    cutTWithin += cropEnd - cropStart

            if matchedEntry is not None:
                newEntryList.append(matchedEntry)

        if rebaseToZero is True:
            newEntryList = [
                (startT - cropStart, stopT - cropStart, label)
                for startT, stopT, label in newEntryList
            ]
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        # Create subtier
        croppedTier = IntervalTier(self.name, newEntryList, minT, maxT)

        # DEBUG info
        #         debugInfo = (subTier, cutTStart, cutTWithin, cutTEnd,
        #                      firstIntervalKeptProportion, lastIntervalKeptProportion)

        return croppedTier

    def difference(self, tier):
        """
        Takes the set difference of this tier and the given one

        Any overlapping portions of entries with entries in this textgrid
        will be removed from the returned tier.

        Args:
            tier (IntervalTier):

        Returns:
            IntervalTier: the modified version of the current tier
        """
        retTier = self.new()

        for entry in tier.entryList:
            retTier = retTier.eraseRegion(
                entry[0], entry[1], collisionCode="truncate", doShrink=False
            )

        return retTier

    def editTimestamps(self, offset, allowOvershoot=False):
        """
        Modifies all timestamps by a constant amount

        Args:
            offset (start): the amount to shift all intervals
            allowOvershoot (bool): if True, an interval can
                go beyond the bounds of the textgrid

        Returns:
            IntervalTier: the modified version of the current tier
        """

        newEntryList = []
        for start, stop, label in self.entryList:

            newStart = offset + start
            newStop = offset + stop
            if allowOvershoot is not True:
                assert newStart >= self.minTimestamp
                assert newStop <= self.maxTimestamp

            if newStop < 0:
                continue
            if newStart < 0:
                newStart = 0

            if newStart < 0:
                continue

            newEntryList.append((newStart, newStop, label))

        # Determine new min and max timestamps
        newMin = min([entry[0] for entry in newEntryList])
        newMax = max([entry[1] for entry in newEntryList])

        if newMin > self.minTimestamp:
            newMin = self.minTimestamp

        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp

        return IntervalTier(self.name, newEntryList, newMin, newMax)

    def eraseRegion(self, start, stop, collisionCode=None, doShrink=True):
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float):
            stop (float):
            collisionCode (bool): determines the behavior when the region to
                erase overlaps with existing intervals. One of ['truncate',
                'categorical', None]
                - 'truncate' partially contained entries will have the portion
                    removed that overlaps with the target entry
                - 'categorical' all entries that overlap, even partially, with
                    the target entry will be completely removed
                - None or any other value throws AssertionError
            doShrink (bool): if True, moves leftward by (/stop/ - /start/)
                amount, each item that occurs after /stop/

        Returns:
            IntervalTier: the modified version of the current tier
        """

        matchList = self.crop(start, stop, "lax", False).entryList
        newTier = self.new()

        # if the collisionCode is not properly set it isn't clear what to do
        assert collisionCode in ["truncate", "categorical"]

        if len(matchList) == 0:
            pass
        else:
            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for tmpEntry in matchList[::-1]:
                newTier.deleteEntry(tmpEntry)

            # If we're only truncating, reinsert entries on the left and
            # right edges
            if collisionCode == "truncate":

                # Check left edge
                if matchList[0][0] < start:
                    newEntry = (matchList[0][0], start, matchList[0][-1])
                    newTier.entryList.append(newEntry)

                # Check right edge
                if matchList[-1][1] > stop:
                    newEntry = (stop, matchList[-1][1], matchList[-1][-1])
                    newTier.entryList.append(newEntry)

        if doShrink is True:

            diff = stop - start
            newEntryList = []
            for entry in newTier.entryList:
                if entry[1] <= start:
                    newEntryList.append(entry)
                elif entry[0] >= stop:
                    newEntryList.append((entry[0] - diff, entry[1] - diff, entry[2]))

            # Special case: an interval that spanned the deleted
            # section
            for i in range(0, len(newEntryList) - 1):
                rightEdge = newEntryList[i][1] == start
                leftEdge = newEntryList[i + 1][0] == start
                sameLabel = newEntryList[i][2] == newEntryList[i + 1][2]
                if rightEdge and leftEdge and sameLabel:
                    newEntry = (
                        newEntryList[i][0],
                        newEntryList[i + 1][1],
                        newEntryList[i][2],
                    )

                    newEntryList.pop(i + 1)
                    newEntryList.pop(i)
                    newEntryList.insert(i, newEntry)

                    # Only one interval can span the deleted section,
                    # so if we've found it, move on
                    break

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList, maxTimestamp=newMax)

        return newTier

    def getValuesInIntervals(self, dataTupleList):
        """
        Returns data from dataTupleList contained in labeled intervals

        dataTupleList should be of the form:
        [(time1, value1a, value1b,...), (time2, value2a, value2b...), ...]
        """

        returnList = []

        for interval in self.entryList:
            intervalDataList = utils.getValuesInInterval(
                dataTupleList, interval[0], interval[1]
            )
            returnList.append((interval, intervalDataList))

        return returnList

    def getNonEntries(self):
        """
        Returns the regions of the textgrid without labels

        This can include unlabeled segments and regions marked as silent.
        """
        entryList = self.entryList
        invertedEntryList = [
            (entryList[i][1], entryList[i + 1][0], "")
            for i in range(len(entryList) - 1)
        ]

        # Remove entries that have no duration (ie lie between two entries
        # that share a border)
        invertedEntryList = [
            entry for entry in invertedEntryList if entry[0] < entry[1]
        ]

        if entryList[0][0] > 0:
            invertedEntryList.insert(0, (0, entryList[0][0], ""))

        if entryList[-1][1] < self.maxTimestamp:
            invertedEntryList.append((entryList[-1][1], self.maxTimestamp, ""))

        invertedEntryList = [
            entry if isinstance(entry, Interval) else Interval(*entry)
            for entry in invertedEntryList
        ]

        return invertedEntryList

    def insertEntry(self, entry, warnFlag=True, collisionCode=None):
        """
        inserts an interval into the tier

        Args:
            entry (list|Interval): the Interval to insert
            warnFlag (bool):
            collisionCode: determines the behavior in the event that intervals
                exist in the insertion area.  One of ['replace', 'merge' None]
                - 'replace' will remove existing items
                - 'merge' will fuse the inserting item with existing items
                - None or any other value will throw a TextgridCollisionException

        if *warnFlag* is True and *collisionCode* is not None,
        the user is notified of each collision

        Returns:
            IntervalTier: the modified version of the current tier
        """
        startTime, endTime = entry[:2]

        matchList = self.crop(startTime, endTime, "lax", False).entryList

        if len(matchList) == 0:
            self.entryList.append(entry)

        elif collisionCode.lower() == "replace":
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            self.entryList.append(entry)

        elif collisionCode.lower() == "merge":
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            matchList.append(entry)
            matchList.sort()  # By starting time

            newEntry = (
                min([entry[0] for entry in matchList]),
                max([entry[1] for entry in matchList]),
                "-".join([entry[2] for entry in matchList]),
            )
            self.entryList.append(Interval(*newEntry))

        else:
            raise TextgridCollisionException(self.name, entry, matchList)

        self.sort()

        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(entry), str(matchList), self.name)))

    def insertSpace(self, start, duration, collisionCode=None):
        """
        Inserts a blank region into the tier

        Args:
            start (float):
            duration (float)
            collisionCode (str): determines the behavior that occurs if
                an interval stradles the starting pointone of ['stretch',
                'split', 'no change']
                - 'stretch' stretches the interval by /duration/ amount
                - 'split' splits the interval into two--everything to the
                    right of 'start' will be advanced by 'duration' seconds
                - 'no change' leaves the interval as is with no change

        Returns:
            IntervalTier: the modified version of the current tier
        """

        # if the collisionCode is not properly set it isn't clear what to do
        assert collisionCode in ["stretch", "split", "no change"]

        newEntryList = []
        for entry in self.entryList:
            # Entry exists before the insertion point
            if entry[1] <= start:
                newEntryList.append(entry)
            # Entry exists after the insertion point
            elif entry[0] >= start:
                newEntryList.append(
                    (entry[0] + duration, entry[1] + duration, entry[2])
                )
            # Entry straddles the insertion point
            elif entry[0] <= start and entry[1] > start:
                if collisionCode == "stretch":
                    newEntryList.append((entry[0], entry[1] + duration, entry[2]))
                elif collisionCode == "split":
                    # Left side of the split
                    newEntryList.append((entry[0], start, entry[2]))
                    # Right side of the split
                    newEntryList.append(
                        (
                            start + duration,
                            start + duration + (entry[1] - start),
                            entry[2],
                        )
                    )
                elif collisionCode == "no change":
                    newEntryList.append(entry)

        newTier = self.new(
            entryList=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def intersection(self, tier):
        """
        Takes the set intersection of this tier and the given one

        Only intervals that exist in both tiers will remain in the
        returned tier.  If intervals partially overlap, only the overlapping
        portion will be returned.

        Args:
            tier (IntervalTier): the tier to intersect with

        Returns:
            IntervalTier: the modified version of the current tier
        """
        retEntryList = []
        for start, stop, label in tier.entryList:
            subTier = self.crop(start, stop, "truncated", False)

            # Combine the labels in the two tiers
            stub = "%s-%%s" % label
            subEntryList = [
                (subEntry[0], subEntry[1], stub % subEntry[2])
                for subEntry in subTier.entryList
            ]

            retEntryList.extend(subEntryList)

        newName = "%s-%s" % (self.name, tier.name)

        retTier = self.new(newName, retEntryList)

        return retTier

    def morph(self, targetTier, filterFunc=None):
        """
        Morphs the duration of segments in this tier to those in another

        This preserves the labels and the duration of silence in
        this tier while changing the duration of labeled segments.

        Args:
            targetTier (IntervalTier):
            filterFunc (functor): if specified, filters entries. The
                functor takes one argument, an Interval. It returns true
                if the Interval should be modified and false if not.

        Returns:
            IntervalTier: the modified version of the current tier
        """
        cumulativeAdjustAmount = 0
        lastFromEnd = 0
        newEntryList = []
        allPoints = [self.entryList, targetTier.entryList]
        for fromEntry, targetEntry in utils.safeZip(allPoints, True):

            fromStart, fromEnd, fromLabel = fromEntry
            targetStart, targetEnd = targetEntry[:2]

            # fromStart - lastFromEnd -> was this interval and the
            # last one adjacent?
            toStart = (fromStart - lastFromEnd) + cumulativeAdjustAmount

            currAdjustAmount = fromEnd - fromStart
            if filterFunc is None or filterFunc(fromLabel):
                currAdjustAmount = targetEnd - targetStart

            toEnd = cumulativeAdjustAmount = toStart + currAdjustAmount
            newEntryList.append((toStart, toEnd, fromLabel))

            lastFromEnd = fromEnd

        newMin = self.minTimestamp
        cumulativeDifference = newEntryList[-1][1] - self.entryList[-1][1]
        newMax = self.maxTimestamp + cumulativeDifference

        return IntervalTier(self.name, newEntryList, newMin, newMax)


class Textgrid:
    def __init__(self):
        "A container that stores and operates over interval and point tiers"
        self.tierNameList = []  # Preserves the order of the tiers
        self.tierDict = {}

        self.minTimestamp = None
        self.maxTimestamp = None

    def __eq__(self, other):
        isEqual = True
        isEqual &= myMath.isclose(self.minTimestamp, other.minTimestamp)
        isEqual &= myMath.isclose(self.maxTimestamp, other.maxTimestamp)

        isEqual &= self.tierNameList == other.tierNameList
        if isEqual:
            for tierName in self.tierNameList:
                isEqual &= self.tierDict[tierName] == other.tierDict[tierName]

        return isEqual

    def addTier(self, tier, tierIndex=None):
        """
        Add a tier to this textgrid.

        Args:
            tier (TextgridTier):
            tierIndex (int): if specified, insert the tier into the specified position

        Returns:
            None
        """

        assert tier.name not in list(self.tierDict.keys())

        if tierIndex is None:
            self.tierNameList.append(tier.name)
        else:
            self.tierNameList.insert(tierIndex, tier.name)

        self.tierDict[tier.name] = tier

        minV = tier.minTimestamp
        if self.minTimestamp is None or minV < self.minTimestamp:
            self.minTimestamp = minV

        maxV = tier.maxTimestamp
        if self.maxTimestamp is None or maxV > self.maxTimestamp:
            self.maxTimestamp = maxV

    def appendTextgrid(self, tg, onlyMatchingNames=True):
        """
        Append one textgrid to the end of this one

        Args:
            tg (Textgrid): the tier to add to this one
            onlyMatchingNames (bool): if False, tiers that don't appear in both
                textgrids will also appear

        Returns:
            Textgrid: the modified version of the current textgrid
        """
        retTG = Textgrid()

        minTime = self.minTimestamp
        maxTime = self.maxTimestamp + tg.maxTimestamp

        # Get all tier names.  Ordered first by this textgrid and
        # then by the other textgrid.
        combinedTierNameList = self.tierNameList
        for tierName in tg.tierNameList:
            if tierName not in combinedTierNameList:
                combinedTierNameList.append(tierName)

        # Determine the tier names that will be in the final textgrid
        finalTierNameList = []
        if onlyMatchingNames is False:
            finalTierNameList = combinedTierNameList
        else:
            for tierName in combinedTierNameList:
                if tierName in self.tierNameList:
                    if tierName in tg.tierNameList:
                        finalTierNameList.append(tierName)

        # Add tiers from this textgrid
        for tierName in self.tierNameList:
            if tierName in finalTierNameList:
                tier = self.tierDict[tierName]
                retTG.addTier(tier)

        # Add tiers from the given textgrid
        for tierName in tg.tierNameList:
            if tierName in finalTierNameList:
                appendTier = tg.tierDict[tierName]
                appendTier = appendTier.new(minTimestamp=minTime, maxTimestamp=maxTime)

                appendTier = appendTier.editTimestamps(self.maxTimestamp)

                if tierName in retTG.tierNameList:
                    tier = retTG.tierDict[tierName]
                    newEntryList = retTG.tierDict[tierName].entryList
                    newEntryList += appendTier.entryList

                    tier = tier.new(
                        entryList=newEntryList,
                        minTimestamp=minTime,
                        maxTimestamp=maxTime,
                    )
                    retTG.replaceTier(tierName, tier)

                else:
                    tier = appendTier
                    tier = tier.new(minTimestamp=minTime, maxTimestamp=maxTime)
                    retTG.addTier(tier)

        return retTG

    def crop(self, cropStart, cropEnd, mode, rebaseToZero):
        """
        Creates a textgrid where all intervals fit within the crop region

        Args:
            cropStart (float):
            cropEnd (float):
            mode (str): one of ['strict', 'lax', 'truncated']
                - 'strict', only intervals wholly contained by the crop
                    interval will be kept
                - 'lax', partially contained intervals will be kept
                - 'truncated', partially contained intervals will be
                    truncated to fit within the crop region.
            rebaseToZero (bool): if True, the cropped textgrid values will be
                subtracted by the cropStart

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        assert mode in ["strict", "lax", "truncated"]

        newTG = Textgrid()

        if rebaseToZero is True:
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd
        newTG.minTimestamp = minT
        newTG.maxTimestamp = maxT
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            newTier = tier.crop(cropStart, cropEnd, mode, rebaseToZero)
            newTG.addTier(newTier)

        return newTG

    def eraseRegion(self, start, stop, doShrink=True):
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float):
            stop (float):
            doShrink (bool): if True, all entries appearing after the
                erased interval will be shifted to fill the void (ie
                the duration of the textgrid will be reduced by
                *start* - *stop*)

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        diff = stop - start

        maxTimestamp = self.maxTimestamp
        if doShrink is True:
            maxTimestamp -= diff

        newTG = Textgrid()
        for name in self.tierNameList:
            tier = self.tierDict[name]
            tier = tier.eraseRegion(start, stop, "truncate", doShrink)
            newTG.addTier(tier)

        newTG.maxTimestamp = maxTimestamp

        return newTG

    def editTimestamps(self, offset, allowOvershoot=False):
        """
        Modifies all timestamps by a constant amount

        Args:
            offset (float): the amount to offset in seconds
            allowOvershoot (bool): if True, entries can go
                beyond the min and max timestamp set by the
                Textgrid

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        tg = Textgrid()
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            if len(tier.entryList) > 0:
                tier = tier.editTimestamps(offset, allowOvershoot)

            tg.addTier(tier)

        return tg

    def insertSpace(self, start, duration, collisionCode=None):
        """
        Inserts a blank region into a textgrid

        Every item that occurs after *start* will be pushed back by
        *duration* seconds

        Args:
            start (float):
            duration (float):
            collisionCode (str): Determines behaviour in the event that an
                interval stradles the starting point.
                One of ['stretch', 'split', 'no change', None]
                - 'stretch' stretches the interval by /duration/ amount
                - 'split' splits the interval into two--everything to the
                    right of 'start' will be advanced by 'duration' seconds
                - 'no change' leaves the interval as is with no change
                - None or any other value throws an AssertionError

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        newTG = Textgrid()
        newTG.minTimestamp = self.minTimestamp
        newTG.maxTimestamp = self.maxTimestamp + duration

        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            newTier = tier.insertSpace(start, duration, collisionCode)
            newTG.addTier(newTier)

        return newTG

    def mergeTiers(self, includeFunc=None, tierList=None, preserveOtherTiers=True):
        """
        Combine tiers

        Args:
            includeFunc (functor): regulates which intervals to include in the
                merging with all others being tossed (default accepts all)
            tierList (list): A list of tier names to combine. If none, combine
                all tiers.
            preserveOtherTiers (bool): If false, uncombined tiers are not
                included in the output.

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        if tierList is None:
            tierList = self.tierNameList

        if includeFunc is None:
            includeFunc = lambda entryList: True

        # Determine the tiers to merge
        intervalTierNameList = []
        pointTierNameList = []
        for tierName in tierList:
            tier = self.tierDict[tierName]
            if isinstance(tier, IntervalTier):
                intervalTierNameList.append(tierName)
            elif isinstance(tier, PointTier):
                pointTierNameList.append(tierName)

        # Merge the interval tiers
        intervalTier = None
        if len(intervalTierNameList) > 0:
            intervalTier = self.tierDict[intervalTierNameList.pop(0)]
        for tierName in intervalTierNameList:
            intervalTier = intervalTier.union(self.tierDict[tierName])

        # Merge the point tiers
        pointTier = None
        if len(pointTierNameList) > 0:
            pointTier = self.tierDict[pointTierNameList.pop(0)]
        for tierName in pointTierNameList:
            pointTier = pointTier.merge(self.tierDict[tierName])

        # Create the final textgrid to output
        tg = Textgrid()

        if intervalTier is not None:
            tg.addTier(intervalTier)

        if pointTier is not None:
            tg.addTier(pointTier)

        return tg

    def new(self):
        """Returns a copy of this Textgrid"""
        return copy.deepcopy(self)

    def renameTier(self, oldName, newName):
        oldTier = self.tierDict[oldName]
        tierIndex = self.tierNameList.index(oldName)
        self.removeTier(oldName)
        self.addTier(oldTier.new(newName, oldTier.entryList), tierIndex)

    def removeTier(self, name):
        self.tierNameList.pop(self.tierNameList.index(name))
        return self.tierDict.pop(name)

    def replaceTier(self, name, newTier):
        tierIndex = self.tierNameList.index(name)
        self.removeTier(name)
        self.addTier(newTier, tierIndex)