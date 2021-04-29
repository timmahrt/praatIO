"""
Functions for reading/writing/manipulating textgrid files.

This file contains the main data structures for representing Textgrid data:
Textgrid, IntervalTier, and PointTier

A Textgrid is a container for multiple annotation tiers.  Tiers can contain
either interval data (IntervalTier) or point data (PointTier).
Tiers in a Textgrid are ordered and must contain a unique name.

openTextgrid() can be used to open a textgrid file.
Textgrid.save() can be used to save a Textgrid object to a file.

see the **examples/** directory for examples using textgrid.py
"""

import io
import re
import copy
from typing import (
    Callable,
    List,
    Tuple,
    Optional,
    TypeVar,
    Union,
    Type,
    Any,
    Dict,
)
from abc import ABC, abstractmethod

from typing_extensions import Literal, Final


from praatio.utilities.constants import (
    Interval,
    Point,
    INTERVAL_TIER,
    POINT_TIER,
    TextgridFormats,
    MIN_INTERVAL_LENGTH,
)
from praatio.utilities import errors
from praatio.utilities import myMath
from praatio.utilities import textgrid_io
from praatio.utilities import utils

T = TypeVar("T", bound="TextgridTier")

# CollisionCode = enum.Enum("CollisionCode", "REPLACE MERGE")

# WhiteSpaceCollisionCode = enum.Enum(
#     "WhiteSpaceCollisionCode", "STRETCH SPLIT NO_CHANGE"
# )


class IntervalCollision:
    REPLACE: Final = "replace"
    MERGE: Final = "merge"


class WhitespaceCollision:
    STRETCH: Final = "stretch"
    SPLIT: Final = "split"
    NO_CHANGE: Final = "no_change"


class CropCollision:
    STRICT: Final = "strict"
    LAX: Final = "lax"
    TRUNCATED: Final = "truncated"


class EraseCollision:
    TRUNCATE: Final = "truncate"
    CATEGORICAL: Final = "categorical"


class TextgridTier(ABC):

    tierType: str
    entryType: Union[Type[Point], Type[Interval]]

    def __init__(
        self,
        name: str,
        entryList: List,
        minT: float,
        maxT: float,
    ):
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

    def appendTier(self, tier: "TextgridTier") -> "TextgridTier":
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

    def find(
        self,
        matchLabel: str,
        substrMatchFlag: bool = False,
        usingRE: bool = False,
    ) -> List[int]:
        """
        Returns the index of all intervals that match the given label

        Args:
            matchLabel (str): the label to search for
            substrMatchFlag (bool): if True, match any label containing matchLabel.
                if False, label must be the same as matchLabel.
            usingRE (bool): if True, matchLabel is interpreted as a regular expression

        Returns:
            List: A list of indicies
        """
        returnList = []
        if usingRE is True:
            for i, entry in enumerate(self.entryList):
                matchList = re.findall(matchLabel, entry.label, re.I)
                if matchList != []:
                    returnList.append(i)
        else:
            for i, entry in enumerate(self.entryList):
                if not substrMatchFlag:
                    if entry.label == matchLabel:
                        returnList.append(i)
                else:
                    if matchLabel in entry.label:
                        returnList.append(i)

        return returnList

    def new(
        self: T,
        name: Optional[str] = None,
        entryList: Optional[list] = None,
        minTimestamp: Optional[float] = None,
        maxTimestamp: Optional[float] = None,
    ) -> T:
        """Make a new tier derived from the current one"""
        if name is None:
            name = self.name
        if entryList is None:
            entryList = copy.deepcopy(self.entryList)
            entryList = [
                self.entryType(*entry)
                if isinstance(entry, tuple) or isinstance(entry, list)
                else entry
                for entry in entryList
            ]
        if minTimestamp is None:
            minTimestamp = self.minTimestamp
        if maxTimestamp is None:
            maxTimestamp = self.maxTimestamp
        return type(self)(name, entryList, minTimestamp, maxTimestamp)

    def sort(self) -> None:
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

    def union(self, tier: "TextgridTier") -> "TextgridTier":
        """
        The given tier is set unioned to this tier.

        All entries in the given tier are added to the current tier.
        Overlapping entries are merged.
        """
        retTier = self.new()

        for entry in tier.entryList:
            retTier.insertEntry(entry, False, collisionCode=IntervalCollision.MERGE)

        retTier.sort()

        return retTier

    @abstractmethod
    def editTimestamps(
        self, offset: float, allowOvershoot: bool = False
    ) -> "TextgridTier":
        pass

    @abstractmethod
    def insertEntry(
        self,
        entry,
        warnFlag: bool = True,
        collisionCode: Optional[Literal["replace", "merge"]] = None,
    ) -> None:
        pass

    @abstractmethod
    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionCode: Optional[Literal["truncate", "categorical"]] = None,
        doShrink: bool = True,
    ) -> "TextgridTier":
        pass

    @abstractmethod
    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "TextgridTier":
        pass

    @abstractmethod
    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionCode: Optional[Literal["stretch", "split", "no_change"]] = None,
    ) -> "TextgridTier":
        pass

    @abstractmethod
    def deleteEntry(self, entry) -> None:
        pass


class PointTier(TextgridTier):

    tierType = POINT_TIER
    entryType = Point

    def __init__(
        self,
        name: str,
        entryList: List[Point],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
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

        try:
            resolvedMinT = min(timeList)
            resolvedMaxT = max(timeList)
        except ValueError:
            raise errors.TimelessTextgridTierException()

        super(PointTier, self).__init__(name, entryList, resolvedMinT, resolvedMaxT)

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"] = CropCollision.LAX,
        rebaseToZero: bool = True,
    ) -> "PointTier":
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
            timestamp = entry.time

            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntryList.append(entry)

        if rebaseToZero is True:
            newEntryList = [
                Point(timeV - cropStart, label) for timeV, label in newEntryList
            ]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return PointTier(self.name, newEntryList, minT, maxT)

    def deleteEntry(self, entry: Point) -> None:
        """Removes an entry from the entryList"""
        self.entryList.pop(self.entryList.index(entry))

    def editTimestamps(
        self, offset: float, allowOvershoot: bool = False
    ) -> "PointTier":
        """
        Modifies all timestamps by a constant amount

        Args:
            offset (float):
            allowOvershoot (bool): if True, an interval can go beyond
                the bounds of the textgrid

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntryList: List[Point] = []
        for timestamp, label in self.entryList:

            newTimestamp = timestamp + offset
            if not allowOvershoot:
                assert newTimestamp > self.minTimestamp
                assert newTimestamp <= self.maxTimestamp

            if newTimestamp < 0:
                continue

            newEntryList.append(Point(newTimestamp, label))

        # Determine new min and max timestamps
        timeList = [float(point.time) for point in newEntryList]
        newMin = min(timeList)
        newMax = max(timeList)

        if newMin > self.minTimestamp:
            newMin = self.minTimestamp

        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp

        return PointTier(self.name, newEntryList, newMin, newMax)

    def getValuesAtPoints(
        self,
        dataTupleList: List[Tuple[float, ...]],
        fuzzyMatching: bool = False,
    ) -> List[Tuple[float, str, Any]]:
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

        currentIndex = 0
        retList = []

        sortedDataTupleList = sorted(dataTupleList)
        for timestamp, label in self.entryList:
            retTuple = utils.getValueAtTime(
                timestamp,
                sortedDataTupleList,
                fuzzyMatching=fuzzyMatching,
                startI=currentIndex,
            )
            retTime, retVal, currentIndex = retTuple
            retList.append((retTime, label, retVal))

        return retList

    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionCode: Optional[Literal["truncate", "categorical"]] = None,
        doShrink: bool = True,
    ) -> "PointTier":
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float): the start of the deletion interval
            end (float): the end of the deletion interval
            collisionCode (str): Ignored for the moment (added for compatibility with
                eraseRegion() for Interval Tiers)
            doShrink (bool): if True, moves leftward by (/end/ - /start/) all points
                to the right of /end/

        Returns:
            PointTier: the modified version of the current tier
        """

        newTier = self.new()
        croppedTier = newTier.crop(start, end, CropCollision.TRUNCATED, False)
        matchList = croppedTier.entryList

        if len(matchList) == 0:
            pass
        else:

            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for point in matchList[::-1]:
                newTier.deleteEntry(point)

        if doShrink is True:
            newEntryList = []
            diff = end - start
            for point in newTier.entryList:
                if point.time < start:
                    newEntryList.append(point)
                elif point.time > end:
                    newEntryList.append(Point(point.time - diff, point.label))

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList, maxTimestamp=newMax)

        return newTier

    def insertEntry(
        self,
        entry: Point,
        warnFlag: bool = True,
        collisionCode: Optional[Literal["replace", "merge"]] = None,
    ) -> None:
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
        if not isinstance(entry, Point):
            newPoint = Point(entry[0], entry[1])
        else:
            newPoint = entry

        matchList = []
        i = None
        for i, point in self.entryList:
            if point.time == newPoint.time:
                matchList.append(point)
                break

        if len(matchList) == 0:
            self.entryList.append(newPoint)

        elif collisionCode == IntervalCollision.REPLACE:
            self.deleteEntry(self.entryList[i])
            self.entryList.append(newPoint)

        elif collisionCode == IntervalCollision.MERGE:
            oldPoint = self.entryList[i]
            mergedPoint = Point(
                newPoint.time, "-".join([oldPoint.label, newPoint.label])
            )
            self.deleteEntry(self.entryList[i])
            self.entryList.append(mergedPoint)

        else:
            raise errors.TextgridCollisionException(self.name, point, matchList)

        self.sort()

        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(entry), str(matchList), self.name)))

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionCode: Optional[Literal["stretch", "split", "no_change"]] = None,
    ) -> "PointTier":
        """
        Inserts a region into the tier

        Args:
            start (float): the start time to insert a space at
            duration (float): the duration of the space to insert
            collisionCode (str): Ignored for the moment (added for compatibility
                with insertSpace() for Interval Tiers)

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntryList = []
        for point in self.entryList:
            if point.time <= start:
                newEntryList.append(point)
            elif point.time > start:
                newEntryList.append(Point(point.time + duration, point.label))

        newTier = self.new(
            entryList=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier


class IntervalTier(TextgridTier):

    tierType = INTERVAL_TIER
    entryType = Interval

    def __init__(
        self,
        name: str,
        entryList: List[Interval],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
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
            Interval(float(start), float(end), label) for start, end, label in entryList
        ]

        if minT is not None:
            minT = float(minT)
        if maxT is not None:
            maxT = float(maxT)

        # Prevent poorly-formed textgrids from being created
        for entry in entryList:
            if entry[0] >= entry[1]:
                fmtStr = "Anomaly: startTime=%f, endTime=%f, label=%s"
                print((fmtStr % (entry[0], entry[1], entry[2])))
            assert entry[0] < entry[1]

        # Remove whitespace
        tmpEntryList = []
        for start, end, label in entryList:
            tmpEntryList.append(Interval(start, end, label.strip()))
        entryList = tmpEntryList

        # Determine the minimum and maximum timestamps
        minTimeList = [subList[0] for subList in entryList]
        maxTimeList = [subList[1] for subList in entryList]

        if minT is not None:
            minTimeList.append(minT)
        if maxT is not None:
            maxTimeList.append(maxT)

        try:
            resolvedMinT = min(minTimeList)
            resolvedMaxT = max(maxTimeList)
        except ValueError:
            raise errors.TimelessTextgridTierException()

        super(IntervalTier, self).__init__(name, entryList, resolvedMinT, resolvedMaxT)

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "IntervalTier":
        """
        Creates a new tier with all entries that fit inside the new interval

        Args:
            cropStart (float):
            cropEnd (float):
            mode (CropMode): one of ['strict', 'lax', or 'truncated']
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

        assert mode in [
            CropCollision.STRICT,
            CropCollision.LAX,
            CropCollision.TRUNCATED,
        ]

        # Debugging variables
        # cutTStart = 0
        cutTWithin = 0.0
        # cutTEnd = 0
        # firstIntervalKeptProportion = 0
        # lastIntervalKeptProportion = 0

        newEntryList = []
        for entry in self.entryList:
            matchedEntry = None

            # Don't need to investigate if the interval is before or after
            # the crop region
            if entry.end <= cropStart or entry.start >= cropEnd:
                continue

            # Determine if the current subEntry is wholly contained
            # within the superEntry
            if entry.start >= cropStart and entry.end <= cropEnd:
                matchedEntry = entry

            # If it is only partially contained within the superEntry AND
            # inclusion is 'lax', include it anyways
            elif mode == "lax" and (entry.start >= cropStart or entry.end <= cropEnd):
                matchedEntry = entry

            # If not strict, include partial tiers on the edges
            # -- regardless, record how much information was lost
            #        - for strict=True, the total time of the cut interval
            #        - for strict=False, the portion of the interval that lies
            #            outside the new interval

            # The current interval stradles the end of the new interval
            elif entry.start >= cropStart and entry.end > cropEnd:
                # cutTEnd = intervalEnd - cropEnd
                # lastIntervalKeptProportion = (cropEnd - intervalStart) / (
                #    intervalEnd - intervalStart
                # )

                if mode == "truncated":
                    matchedEntry = (entry.start, cropEnd, entry.label)

                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval stradles the start of the new interval
            elif entry.start < cropStart and entry.end <= cropEnd:
                # cutTStart = cropStart - intervalStart
                # firstIntervalKeptProportion = (intervalEnd - cropStart) / (
                #     intervalEnd - intervalStart
                # )
                if mode == "truncated":
                    matchedEntry = (cropStart, entry.end, entry.label)
                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval contains the new interval completely
            elif entry.start <= cropStart and entry.end >= cropEnd:

                if mode == "lax":
                    matchedEntry = entry
                elif mode == "truncated":
                    matchedEntry = (cropStart, cropEnd, entry.label)
                else:
                    cutTWithin += cropEnd - cropStart

            if matchedEntry is not None:
                newEntryList.append(matchedEntry)

        if rebaseToZero is True:
            newEntryList = [
                Interval(start - cropStart, end - cropStart, label)
                for start, end, label in newEntryList
            ]
            minT = 0.0
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

    def deleteEntry(self, entry: Interval) -> None:
        """Removes an entry from the entryList"""
        self.entryList.pop(self.entryList.index(entry))

    def difference(self, tier: "IntervalTier") -> "IntervalTier":
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
                entry.start,
                entry.end,
                collisionCode=EraseCollision.TRUNCATE,
                doShrink=False,
            )

        return retTier

    def editTimestamps(
        self, offset: float, allowOvershoot: bool = False
    ) -> "IntervalTier":
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
        for interval in self.entryList:

            newStart = offset + interval.start
            newEnd = offset + interval.end
            if allowOvershoot is not True:
                assert newStart >= self.minTimestamp
                assert newEnd <= self.maxTimestamp

            if newEnd < 0:
                continue
            if newStart < 0:
                newStart = 0

            if newStart < 0:
                continue

            newEntryList.append(Interval(newStart, newEnd, interval.label))

        # Determine new min and max timestamps
        newMin = min([interval.start for interval in newEntryList])
        newMax = max([interval.end for interval in newEntryList])

        if newMin > self.minTimestamp:
            newMin = self.minTimestamp

        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp

        return IntervalTier(self.name, newEntryList, newMin, newMax)

    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionCode: Optional[Literal["truncate", "categorical"]] = None,
        doShrink: bool = True,
    ) -> "IntervalTier":
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float):
            end (float):
            collisionCode (EraseRegionCollisionCode): determines the behavior when
                the region to erase overlaps with existing intervals. One of
                ['truncate', 'categorical', None]
                - 'truncate' partially contained entries will have the portion
                    removed that overlaps with the target entry
                - 'categorical' all entries that overlap, even partially, with
                    the target entry will be completely removed
                - None or any other value throws AssertionError
            doShrink (bool): if True, moves leftward by (/end/ - /start/)
                amount, each item that occurs after /end/

        Returns:
            IntervalTier: the modified version of the current tier
        """

        matchList = self.crop(start, end, CropCollision.LAX, False).entryList
        newTier = self.new()

        # if the collisionCode is not properly set it isn't clear what to do
        assert collisionCode in [
            EraseCollision.TRUNCATE,
            EraseCollision.CATEGORICAL,
        ]

        if len(matchList) == 0:
            pass
        else:
            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for interval in matchList[::-1]:
                newTier.deleteEntry(interval)

            # If we're only truncating, reinsert entries on the left and
            # right edges
            # if categorical, it doesn't make it into the list at all
            if collisionCode == EraseCollision.TRUNCATE:

                # Check left edge
                if matchList[0].start < start:
                    newEntry = Interval(matchList[0].start, start, matchList[0].label)
                    newTier.entryList.append(newEntry)

                # Check right edge
                if matchList[-1].end > end:
                    newEntry = Interval(end, matchList[-1].end, matchList[-1].label)
                    newTier.entryList.append(newEntry)

        if doShrink is True:

            diff = end - start
            newEntryList = []
            for interval in newTier.entryList:
                if interval.end <= start:
                    newEntryList.append(interval)
                elif interval.start >= end:
                    newEntryList.append(
                        Interval(
                            interval.start - diff, interval.end - diff, interval.label
                        )
                    )

            # Special case: an interval that spanned the deleted
            # section
            for i in range(0, len(newEntryList) - 1):
                rightEdge = newEntryList[i].end == start
                leftEdge = newEntryList[i + 1].start == start
                sameLabel = newEntryList[i].label == newEntryList[i + 1].label
                if rightEdge and leftEdge and sameLabel:
                    newInterval = Interval(
                        newEntryList[i].start,
                        newEntryList[i + 1].end,
                        newEntryList[i].label,
                    )

                    newEntryList.pop(i + 1)
                    newEntryList.pop(i)
                    newEntryList.insert(i, newInterval)

                    # Only one interval can span the deleted section,
                    # so if we've found it, move on
                    break

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList, maxTimestamp=newMax)

        return newTier

    def getValuesInIntervals(self, dataTupleList: List) -> List[Tuple[Interval, List]]:
        """
        Returns data from dataTupleList contained in labeled intervals

        dataTupleList should be of the form:
        [(time1, value1a, value1b,...), (time2, value2a, value2b...), ...]
        """

        returnList = []

        for interval in self.entryList:
            intervalDataList = utils.getValuesInInterval(
                dataTupleList, interval.start, interval.end
            )
            returnList.append((interval, intervalDataList))

        return returnList

    def getNonEntries(self) -> List[Interval]:
        """
        Returns the regions of the textgrid without labels

        This can include unlabeled segments and regions marked as silent.
        """
        entryList = self.entryList
        invertedEntryList = [
            Interval(entryList[i].end, entryList[i + 1].start, "")
            for i in range(len(entryList) - 1)
        ]

        # Remove entries that have no duration (ie lie between two entries
        # that share a border)
        invertedEntryList = [
            interval for interval in invertedEntryList if interval.start < interval.end
        ]

        if entryList[0].start > 0:
            invertedEntryList.insert(0, Interval(0, entryList[0].start, ""))

        if entryList[-1].end < self.maxTimestamp:
            invertedEntryList.append(Interval(entryList[-1].end, self.maxTimestamp, ""))

        invertedEntryList = [
            interval if isinstance(interval, Interval) else Interval(*interval)
            for interval in invertedEntryList
        ]

        return invertedEntryList

    def insertEntry(
        self,
        entry: Interval,
        warnFlag: bool = True,
        collisionCode: Optional[Literal["replace", "merge"]] = None,
    ) -> None:
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
        if not isinstance(entry, Interval):
            interval = Interval(*entry)
        else:
            interval = entry

        matchList = self.crop(
            interval.start, interval.end, CropCollision.LAX, False
        ).entryList

        if len(matchList) == 0:
            self.entryList.append(interval)

        elif collisionCode == IntervalCollision.REPLACE:
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            self.entryList.append(interval)

        elif collisionCode == IntervalCollision.MERGE:
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            matchList.append(interval)
            matchList.sort()  # By starting time

            newInterval = Interval(
                min([tmpInterval.start for tmpInterval in matchList]),
                max([tmpInterval.end for tmpInterval in matchList]),
                "-".join([tmpInterval.label for tmpInterval in matchList]),
            )
            self.entryList.append(newInterval)

        else:
            raise errors.TextgridCollisionException(self.name, interval, matchList)

        self.sort()

        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(interval), str(matchList), self.name)))

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionCode: Optional[Literal["stretch", "split", "no_change"]] = None,
    ) -> "IntervalTier":
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
        assert collisionCode in [
            WhitespaceCollision.STRETCH,
            WhitespaceCollision.SPLIT,
            WhitespaceCollision.NO_CHANGE,
        ]

        newEntryList = []
        for interval in self.entryList:
            # Entry exists before the insertion point
            if interval.end <= start:
                newEntryList.append(interval)
            # Entry exists after the insertion point
            elif interval.start >= start:
                newEntryList.append(
                    Interval(
                        interval.start + duration,
                        interval.end + duration,
                        interval.label,
                    )
                )
            # Entry straddles the insertion point
            elif interval.start <= start and interval.end > start:
                if collisionCode == WhitespaceCollision.STRETCH:
                    newEntryList.append(
                        Interval(
                            interval.start, interval.end + duration, interval.label
                        )
                    )
                elif collisionCode == WhitespaceCollision.SPLIT:
                    # Left side of the split
                    newEntryList.append(Interval(interval.start, start, interval.label))
                    # Right side of the split
                    newEntryList.append(
                        (
                            start + duration,
                            start + duration + (interval.end - start),
                            interval.label,
                        )
                    )
                elif collisionCode == WhitespaceCollision.NO_CHANGE:
                    newEntryList.append(interval)

        newTier = self.new(
            entryList=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def intersection(self, tier: "IntervalTier") -> "IntervalTier":
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
        for interval in tier.entryList:
            subTier = self.crop(
                interval.start, interval.end, CropCollision.TRUNCATED, False
            )

            # Combine the labels in the two tiers
            subEntryList = [
                (
                    subInterval.start,
                    subInterval.end,
                    f"{interval.label}-{subInterval.label}",
                )
                for subInterval in subTier.entryList
            ]

            retEntryList.extend(subEntryList)

        newName = f"{self.name}-{tier.name}"

        retTier = self.new(newName, retEntryList)

        return retTier

    def morph(
        self,
        targetTier: "IntervalTier",
        filterFunc: Optional[Callable[[Interval], bool]] = None,
    ) -> "IntervalTier":
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
        allIntervals = [self.entryList, targetTier.entryList]
        for sourceInterval, targetInterval in utils.safeZip(allIntervals, True):

            # sourceInterval.start - lastFromEnd -> was this interval and the
            # last one adjacent?
            newStart = (sourceInterval.start - lastFromEnd) + cumulativeAdjustAmount

            currAdjustAmount = sourceInterval.end - sourceInterval.start
            if filterFunc is None or filterFunc(sourceInterval.label):
                currAdjustAmount = targetInterval.end - targetInterval.start

            newEnd = cumulativeAdjustAmount = newStart + currAdjustAmount
            newEntryList.append(Interval(newStart, newEnd, sourceInterval.label))

            lastFromEnd = sourceInterval.start

        newMin = self.minTimestamp
        cumulativeDifference = newEntryList[-1].end - self.entryList[-1].end
        newMax = self.maxTimestamp + cumulativeDifference

        return IntervalTier(self.name, newEntryList, newMin, newMax)


class Textgrid:
    def __init__(self):
        "A container that stores and operates over interval and point tiers"
        self.tierNameList: List[str] = []  # Preserves the order of the tiers
        self.tierDict: Dict[str, TextgridTier] = {}

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

    def addTier(self, tier: "TextgridTier", tierIndex: Optional[int] = None) -> None:
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

    def appendTextgrid(
        self, tg: "Textgrid", onlyMatchingNames: bool = True
    ) -> "Textgrid":
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

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "Textgrid":
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

        assert mode in [
            CropCollision.STRICT,
            CropCollision.LAX,
            CropCollision.TRUNCATED,
        ]

        newTG = Textgrid()

        if rebaseToZero is True:
            minT = 0.0
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

    def eraseRegion(
        self, start: float, end: float, doShrink: bool = True
    ) -> "Textgrid":
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float):
            end (float):
            doShrink (bool): if True, all entries appearing after the
                erased interval will be shifted to fill the void (ie
                the duration of the textgrid will be reduced by
                *start* - *end*)

        Returns:
            Textgrid: the modified version of the current textgrid
        """

        diff = end - start

        maxTimestamp = self.maxTimestamp
        if doShrink is True:
            maxTimestamp -= diff

        newTG = Textgrid()
        for name in self.tierNameList:
            tier = self.tierDict[name]
            tier = tier.eraseRegion(start, end, EraseCollision.TRUNCATE, doShrink)
            newTG.addTier(tier)

        newTG.maxTimestamp = maxTimestamp

        return newTG

    def editTimestamps(self, offset: float, allowOvershoot: bool = False) -> "Textgrid":
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

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionCode: Optional[Literal["stretch", "split", "no_change"]] = None,
    ) -> "Textgrid":
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

    def mergeTiers(
        self,
        includeFunc: Optional[Callable] = None,
        tierList: Optional[List[str]] = None,
        preserveOtherTiers: bool = True,
    ) -> "Textgrid":
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

        def acceptAll(_entryList):
            return True

        # TODO: Not being used???
        if includeFunc is None:
            includeFunc = acceptAll

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
                pointTier = pointTier.union(self.tierDict[tierName])

        # Create the final textgrid to output
        tg = Textgrid()

        if intervalTier is not None:
            tg.addTier(intervalTier)

        if pointTier is not None:
            tg.addTier(pointTier)

        return tg

    def new(self) -> "Textgrid":
        """Returns a copy of this Textgrid"""
        return copy.deepcopy(self)

    def save(
        self,
        outputFn: str,
        minimumIntervalLength: float = MIN_INTERVAL_LENGTH,
        minTimestamp: Optional[float] = None,
        maxTimestamp: Optional[float] = None,
        outputFormat: Literal[
            "short_textgrid", "long_textgrid", "json"
        ] = TextgridFormats.SHORT_TEXTGRID,
        ignoreBlankSpaces: bool = False,
    ) -> None:
        tgAsDict = _tgToDictionary(self)
        textgridStr = textgrid_io.getTextgridAsStr(
            tgAsDict,
            minimumIntervalLength,
            minTimestamp,
            maxTimestamp,
            outputFormat,
            ignoreBlankSpaces,
        )

        with io.open(outputFn, "w", encoding="utf-8") as fd:
            fd.write(textgridStr)

    def renameTier(self, oldName: str, newName: str) -> None:
        oldTier = self.tierDict[oldName]
        tierIndex = self.tierNameList.index(oldName)
        self.removeTier(oldName)
        self.addTier(oldTier.new(newName, oldTier.entryList), tierIndex)

    def removeTier(self, name: str) -> "TextgridTier":
        self.tierNameList.pop(self.tierNameList.index(name))
        return self.tierDict.pop(name)

    def replaceTier(self, name: str, newTier: "TextgridTier") -> None:
        tierIndex = self.tierNameList.index(name)
        self.removeTier(name)
        self.addTier(newTier, tierIndex)


def openTextgrid(fnFullPath: str, includeEmptyIntervals: bool = False) -> Textgrid:
    """
    Opens a textgrid file (.TextGrid and .json are both fine)

    Args:
        fnFullPath (str): the path to the textgrid to open
        includeEmptyIntervals (bool): if False, points and intervals with
             an empty label '' are not included in the returned Textgrid

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

    tgAsDict = textgrid_io.parseTextgridStr(data, includeEmptyIntervals)
    return _dictionaryToTg(tgAsDict)


def _tgToDictionary(tg: Textgrid) -> dict:
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


def _dictionaryToTg(tgAsDict: dict) -> Textgrid:
    """Converts a dictionary representation of a textgrid to a Textgrid"""
    tg = Textgrid()
    tg.minTimestamp = tgAsDict["xmin"]
    tg.maxTimestamp = tgAsDict["xmax"]

    for tierAsDict in tgAsDict["tiers"]:
        klass: Union[Type[PointTier], Type[IntervalTier]]
        if tierAsDict["class"] == INTERVAL_TIER:
            klass = IntervalTier
        else:
            klass = PointTier
        tier = klass(
            tierAsDict["name"],
            tierAsDict["entries"],
            tierAsDict["xmin"],
            tierAsDict["xmax"],
        )
        tg.addTier(tier)

    return tg
