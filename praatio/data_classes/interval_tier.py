"""
An IntervalTier is a tier containing an array of intervals -- data that spans a period of time
"""
from typing import Callable, List, Optional, Tuple, Sequence

from typing_extensions import Literal


from praatio.utilities.constants import (
    Interval,
    INTERVAL_TIER,
    CropCollision,
)

from praatio.utilities import errors
from praatio.utilities import utils
from praatio.utilities import constants

from praatio.data_classes import textgrid_tier


def _homogenizeEntries(entries):
    """
    Enforces consistency in intervals

    - converts all entries to intervals
    - removes whitespace in labels
    - sorts values by time
    """
    processedEntries = [
        Interval(float(start), float(end), label.strip())
        for start, end, label in entries
    ]
    processedEntries.sort()
    return processedEntries


def _calculateMinAndMaxTime(entries: Sequence[Interval], minT=None, maxT=None):
    minTimeList = [interval.start for interval in entries]
    maxTimeList = [interval.end for interval in entries]

    if minT is not None:
        minTimeList.append(float(minT))
    if maxT is not None:
        maxTimeList.append(float(maxT))

    try:
        resolvedMinT = min(minTimeList)
        resolvedMaxT = max(maxTimeList)
    except ValueError:
        raise errors.TimelessTextgridTierException()

    return (resolvedMinT, resolvedMaxT)


class IntervalTier(textgrid_tier.TextgridTier):

    tierType = INTERVAL_TIER
    entryType = Interval

    def __init__(
        self,
        name: str,
        entries: List[Interval],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
        """An interval tier is for annotating events that have duration

        The entries is of the form:
        [(startTime1, endTime1, label1), (startTime2, endTime2, label2), ]

        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('erase this region') or numerical data e.g. (average pitch
        values like '132'))
        """
        entries = _homogenizeEntries(entries)
        calculatedMinT, calculatedMaxT = _calculateMinAndMaxTime(entries, minT, maxT)

        super(IntervalTier, self).__init__(
            name, entries, calculatedMinT, calculatedMaxT
        )
        self._validate()

    def _validate(self):
        """An interval tier is invalid if the entries are out of order or overlap with each other"""
        for entry in self.entries:
            if entry.start >= entry.end:
                raise errors.TextgridStateError(
                    f"The start time of an interval ({entry.start}) "
                    f"cannot occur after its end time ({entry.end})"
                )

        for entry, nextEntry in zip(self.entries[0::], self.entries[1::]):
            if entry.end > nextEntry.start:
                raise errors.TextgridStateError(
                    "Two intervals in the same tier overlap in time:\n"
                    f"({entry.start}, {entry.end}, {entry.label}) and ({entry.start}, {entry.end}, {entry.label})"
                )

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "IntervalTier":
        """Creates a new tier with all entries that fit inside the new interval

        Args:
            cropStart:
            cropEnd:
            mode: determines cropping behavior
                - 'strict', only intervals wholly contained by the crop
                    interval will be kept
                - 'lax', partially contained intervals will be kept
                - 'truncated', partially contained intervals will be
                    truncated to fit within the crop region.
            rebaseToZero: if True, the cropped textgrid values
                will be subtracted by the cropStart

        Returns:
            the modified version of the current tier
        """

        utils.validateOption("mode", mode, CropCollision)

        if cropStart >= cropEnd:
            raise errors.ArgumentError(
                f"Crop error: start time ({cropStart}) must occur before end time ({cropEnd})"
            )

        newEntryList = utils.getIntervalsInInterval(
            cropStart, cropEnd, self.entries, mode
        )

        if rebaseToZero is True:
            newSmallestValue = newEntryList[0][0]
            if newSmallestValue < cropStart:
                timeDiff = newSmallestValue
            else:
                timeDiff = cropStart
            newEntryList = [
                Interval(start - timeDiff, end - timeDiff, label)
                for start, end, label in newEntryList
            ]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        croppedTier = IntervalTier(self.name, newEntryList, minT, maxT)

        return croppedTier

    def deleteEntry(self, entry: Interval) -> None:
        """Removes an entry from the entries"""
        self._entries.pop(self._entries.index(entry))

    def difference(self, tier: "IntervalTier") -> "IntervalTier":
        """Takes the set difference of this tier and the given one

        Any overlapping portions of entries with entries in this textgrid
        will be removed from the returned tier.

        Args:
            tier: the tier to subtract from this one

        Returns:
            the modified version of the current tier
        """
        retTier = self.new()

        for entry in tier.entries:
            retTier = retTier.eraseRegion(
                entry.start,
                entry.end,
                collisionMode=constants.EraseCollision.TRUNCATE,
                doShrink=False,
            )

        return retTier

    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "IntervalTier":
        """Modifies all timestamps by a constant amount

        Args:
            offset: the amount to shift all intervals
            reportingMode: Determines the behavior if an entries moves outside
                of minTimestamp or maxTimestamp after being edited

        Returns:
            the modified version of the current tier
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        newEntryList = []
        for interval in self.entries:

            newStart = offset + interval.start
            newEnd = offset + interval.end

            utils.checkIsUndershoot(newStart, self.minTimestamp, errorReporter)
            utils.checkIsOvershoot(newEnd, self.maxTimestamp, errorReporter)

            if newEnd <= 0:
                continue
            if newStart < 0:
                newStart = 0

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
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> "IntervalTier":
        """Makes a region in a tier blank (removes all contained entries)

        Args:
            start:
            end:
            collisionMode: Determines the behavior when the region to erase
                overlaps with existing intervals.
                - 'truncate' partially contained entries will have the portion
                    removed that overlaps with the target entry
                - 'categorical' all entries that overlap, even partially, with
                    the target entry will be completely removed
                - None or any other value throws IntervalCollision
            doShrink: If True, moves leftward by (/end/ - /start/)
                amount, each item that occurs after /end/

        Returns:
            The modified version of the current tier

        Raises:
            CollisionError
        """
        utils.validateOption("collisionMode", collisionMode, constants.EraseCollision)

        matchList = self.crop(start, end, CropCollision.LAX, False).entries
        newTier = self.new()

        if len(matchList) == 0:
            pass
        else:
            if collisionMode == constants.EraseCollision.ERROR:
                raise errors.CollisionError(
                    f"Erase region ({start}, {end})overlapped with an interval. "
                    "If this was expected, consider setting the collisionMode"
                )

            # Remove all the matches from the entries
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for interval in matchList[::-1]:
                newTier.deleteEntry(interval)

            # If we're only truncating, reinsert entries on the left and
            # right edges
            # if categorical, it doesn't make it into the list at all
            if collisionMode == constants.EraseCollision.TRUNCATE:

                # Check left edge
                if matchList[0].start < start:
                    newEntry = Interval(matchList[0].start, start, matchList[0].label)
                    newTier.insertEntry(newEntry)

                # Check right edge
                if matchList[-1].end > end:
                    newEntry = Interval(end, matchList[-1].end, matchList[-1].label)
                    newTier.insertEntry(newEntry)

        if doShrink is True:

            diff = end - start
            newEntryList = []
            for interval in newTier.entries:
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
            newTier = newTier.new(entries=newEntryList, maxTimestamp=newMax)

        return newTier

    def getValuesInIntervals(self, dataTupleList: List) -> List[Tuple[Interval, List]]:
        """Returns data from dataTupleList contained in labeled intervals

        Each labeled interval will get its own list of data values.

        dataTupleList should be of the form:
        [(time1, value1a, value1b,...), (time2, value2a, value2b...), ...]
        """

        returnList = []

        for interval in self.entries:
            intervalDataList = utils.getValuesInInterval(
                dataTupleList, interval.start, interval.end
            )
            returnList.append((interval, intervalDataList))

        return returnList

    def getNonEntries(self) -> List[Interval]:
        """Returns the regions of the textgrid without labels

        This can include unlabeled segments and regions marked as silent.
        """
        entries = self.entries
        invertedEntryList = [
            Interval(entries[i].end, entries[i + 1].start, "")
            for i in range(len(entries) - 1)
        ]

        # Remove entries that have no duration (ie lie between two entries
        # that share a border)
        invertedEntryList = [
            interval for interval in invertedEntryList if interval.start < interval.end
        ]

        if entries[0].start > 0:
            invertedEntryList.insert(0, Interval(0, entries[0].start, ""))

        if entries[-1].end < self.maxTimestamp:
            invertedEntryList.append(Interval(entries[-1].end, self.maxTimestamp, ""))

        invertedEntryList = [
            interval if isinstance(interval, Interval) else Interval(*interval)
            for interval in invertedEntryList
        ]

        return invertedEntryList

    def insertEntry(
        self,
        entry: Interval,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:
        """Inserts an interval into the tier

        Args:
            entry: the Interval to insert
            collisionMode: determines the behavior in the event that intervals
                exist in the insertion area.
                - 'replace' will remove existing items
                - 'merge' will fuse the inserting item with existing items
                - None or any other value will throw a CollisionError
            collisionReportingMode: Determines the behavior if the new entry
                overlaps with an existing one

        Returns:
            the modified version of the current tier
        """
        utils.validateOption(
            "collisionMode", collisionMode, constants.IntervalCollision
        )
        utils.validateOption(
            "collisionReportingMode",
            collisionReportingMode,
            constants.ErrorReportingMode,
        )
        collisionReporter = utils.getErrorReporter(collisionReportingMode)

        if not isinstance(entry, Interval):
            interval = Interval(*entry)
        else:
            interval = entry

        matchList = self.crop(
            interval.start, interval.end, CropCollision.LAX, False
        )._entries

        if len(matchList) == 0:
            self._entries.append(interval)

        elif collisionMode == constants.IntervalCollision.REPLACE:
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            self._entries.append(interval)

        elif collisionMode == constants.IntervalCollision.MERGE:
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            matchList.append(interval)
            matchList.sort()  # By starting time

            newInterval = Interval(
                min([tmpInterval.start for tmpInterval in matchList]),
                max([tmpInterval.end for tmpInterval in matchList]),
                "-".join([tmpInterval.label for tmpInterval in matchList]),
            )
            self._entries.append(newInterval)

        else:
            raise errors.CollisionError(
                "Attempted to insert interval "
                f"({interval.start}, {interval.end}, '{interval.label}') into tier {self.name} "
                "of textgrid but overlapping entries "
                f"{[tuple(interval) for interval in matchList]} "
                "already exist"
            )

        self.sort()

        if self._entries[0][0] < self.minTimestamp:
            self.minTimestamp = self._entries[0][0]

        if self._entries[-1][1] > self.maxTimestamp:
            self.maxTimestamp = self._entries[-1][1]

        if len(matchList) != 0:
            collisionReporter(
                errors.CollisionError,
                f"Collision warning for ({interval}) with items "
                f"({matchList}) of tier '{self.name}'",
            )

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionMode: Literal["stretch", "split", "no_change", "error"],
    ) -> "IntervalTier":
        """Inserts a blank region into the tier

        Args:
            start:
            duration:
            collisionMode: Determines the behavior that occurs if
                an interval stradles the starting point
                - 'stretch' stretches the interval by /duration/ amount
                - 'split' splits the interval into two--everything to the
                    right of 'start' will be advanced by 'duration' seconds
                - 'no change' leaves the interval as is with no change
                - 'error' will stop execution and raise an error

        Returns:
            the modified version of the current tier
        """
        utils.validateOption(
            "collisionMode", collisionMode, constants.WhitespaceCollision
        )

        newEntryList = []
        for interval in self.entries:
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
                if collisionMode == constants.WhitespaceCollision.STRETCH:
                    newEntryList.append(
                        Interval(
                            interval.start, interval.end + duration, interval.label
                        )
                    )
                elif collisionMode == constants.WhitespaceCollision.SPLIT:
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
                elif collisionMode == constants.WhitespaceCollision.NO_CHANGE:
                    newEntryList.append(interval)
                else:
                    raise errors.ArgumentError(
                        f"Collision occured during insertSpace() for interval '{interval}' "
                        f"and given white space insertion interval ({start}, {start + duration})"
                    )

        newTier = self.new(
            entries=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def intersection(self, tier: "IntervalTier", demarcator="-") -> "IntervalTier":
        """Takes the set intersection of this tier and the given one

        - The output will contain one interval for each overlapping pair
          e.g. [(1, 2, 'foo')] and [(1, 1.3, 'bang'), (1.7, 2, 'wizz')]
                -> [(1, 1.3, 'foo-bang'), (1.7, 2, 'foo-wizz')]
        - Only intervals that exist in both tiers will remain in the returned tier.
          e.g. [(1, 2, 'foo'), (3, 4, 'bar')] and [(1, 2, 'bang'), (2, 3, 'wizz')]
                -> [(1, 2, 'foo-bang')]
        - If intervals partially overlap, only the overlapping portion will be returned.
          e.g. [(1, 2, 'foo')] and [(0.5, 1.5, 'bang')]
                -> [(1, 1.5, 'foo-bang')]

        Compare with IntervalTier.mergeLabels

        Args:
            tier: the tier to intersect with
            demarcator: the character to separate the labels of the overlapping intervals

        Returns:
            IntervalTier: the modified version of the current tier
        """
        retEntryList = []
        for interval in tier.entries:
            subTier = self.crop(
                interval.start, interval.end, CropCollision.TRUNCATED, False
            )

            # Combine the labels in the two tiers
            subEntryList = [
                (
                    subInterval.start,
                    subInterval.end,
                    f"{subInterval.label}{demarcator}{interval.label}",
                )
                for subInterval in subTier.entries
            ]

            retEntryList.extend(subEntryList)

        newName = f"{self.name}-{tier.name}"

        retTier = self.new(newName, retEntryList)

        return retTier

    def mergeLabels(
        self, tier: "IntervalTier", demarcator: str = ","
    ) -> "IntervalTier":
        """Merges labels of overlapping tiers into this tier

        - All intervals in this tier will appear in the output; for the given tier, only intervals
          that overlap with content in this tier will appear in the output
          e.g. [(1, 2, 'foo'), (3, 4, 'bar')] and [(1, 2, 'bang'), (2, 3, 'wizz')]
                -> [(1, 2, 'foo(bang)'), (3, 4, 'bar()')]
        - If multiple entries exist in a subinterval, their labels will be concatenated
          e.g. [(1, 2, 'hi')] and [(1, 1.5, 'h'), (1.5, 2, 'ai')] -> [(1, 2, 'hi(h,ai)')]

        compare with IntervalTier.intersection

        Args:
            tier: the tier to intersect with
            demarcator: the string to separate items that fall in the same subinterval

        Returns:
            IntervalTier: the modified version of the current tier
        """
        retEntryList = []
        for interval in self.entries:
            subTier = tier.crop(
                interval.start, interval.end, CropCollision.TRUNCATED, False
            )
            if len(subTier._entries) == 0:
                continue

            subLabel = demarcator.join([entry.label for entry in subTier.entries])
            label = f"{interval.label}({subLabel})"

            start = min(interval.start, subTier._entries[0].start)
            end = max(interval.end, subTier._entries[-1].end)

            intersectedInterval = (
                start,
                end,
                label,
            )

            retEntryList.append(intersectedInterval)

        newName = f"{self.name}-{tier.name}"

        retTier = self.new(newName, retEntryList)

        return retTier

    def morph(
        self,
        targetTier: "IntervalTier",
        filterFunc: Optional[Callable[[str], bool]] = None,
    ) -> "IntervalTier":
        """Morphs the duration of segments in this tier to those in another

        This preserves the labels and the duration of silence in
        this tier while changing the duration of labeled segments.

        Args:
            targetTier:
            filterFunc: if specified, filters entries. The
                functor takes one argument, an Interval. It returns true
                if the Interval should be modified and false if not.

        Returns:
            The modified version of the current tier
        """
        cumulativeAdjustAmount = 0
        newEntryList = []
        allIntervals = [self.entries, targetTier.entries]
        for sourceInterval, targetInterval in utils.safeZip(allIntervals, True):

            # sourceInterval.start - lastFromEnd -> was this interval and the
            # last one adjacent?
            newStart = sourceInterval.start + cumulativeAdjustAmount

            currIntervalDuration = sourceInterval.end - sourceInterval.start
            if filterFunc is None or filterFunc(sourceInterval.label):
                newIntervalDuration = targetInterval.end - targetInterval.start
                cumulativeAdjustAmount += newIntervalDuration - currIntervalDuration
                newEnd = newStart + newIntervalDuration
            else:
                newEnd = newStart + currIntervalDuration

            newEntryList.append(Interval(newStart, newEnd, sourceInterval.label))

        newMin = self.minTimestamp
        cumulativeDifference = newEntryList[-1].end - self.entries[-1].end
        newMax = self.maxTimestamp + cumulativeDifference

        return IntervalTier(self.name, newEntryList, newMin, newMax)

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """Validate this tier

        Args:
            reportingMode (str): Determines the behavior if validation fails.

        Returns:
            True if the tier is valid; False if not
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        isValid = True
        previousInterval = None
        for interval in self.entries:
            if interval.start >= interval.end:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Invalid interval. End time occurs before or on the start time({interval}).",
                )

            if previousInterval and previousInterval.end > interval.start:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Intervals are not sorted in time: "
                    f"[({previousInterval}), ({interval})]",
                )

            if utils.checkIsUndershoot(
                interval.start, self.minTimestamp, errorReporter
            ):
                isValid = False

            if utils.checkIsOvershoot(interval.end, self.maxTimestamp, errorReporter):
                isValid = False

            previousInterval = interval

        return isValid
