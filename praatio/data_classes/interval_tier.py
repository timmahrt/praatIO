"""
An IntervalTier is a tier containing an array of intervals -- data that spans a period of time.
"""
from typing import List, Tuple, Optional, Iterable, Callable, Sequence, Any
from typing_extensions import Literal
from itertools import chain

from praatio import audio
from praatio.utilities.constants import Interval, INTERVAL_TIER
from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils
from praatio.utilities import my_math

from praatio.data_classes.textgrid_tier import TextgridTier


class IntervalTier(TextgridTier[Interval]):
    """An interval tier is for annotating events that have duration."""

    tierType = INTERVAL_TIER
    entryType = Interval

    def __init__(
        self,
        name: str,
        entries: Iterable[Sequence[Any]] = [],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
        super(IntervalTier, self).__init__(name, entries, minT, maxT)
        self._validate()

    def _validate(self):
        """An interval tier is invalid if the entries are out of order or overlapping."""
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
                    f"{entry} and {nextEntry}"
                )

    @property
    def timestamps(self) -> List[float]:
        return sorted(set(chain.from_iterable(entry[:2] for entry in self._entries)))

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "IntervalTier":
        """Create a new tier with all entries that fit inside the new interval.

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

        Raises:
            WrongOption: the mode is not valid
            ArgumentError: cropStart occurs after cropEnd
        """

        utils.validateOption("mode", mode, constants.CropCollision)

        if cropStart >= cropEnd:
            raise errors.ArgumentError(
                f"Crop error: start time ({cropStart}) must occur before end time ({cropEnd})"
            )

        newEntries = utils.getIntervalsInInterval(
            cropStart, cropEnd, self.entries, mode
        )

        if rebaseToZero:
            if newEntries:
                timeDiff = min(newEntries[0].start, cropStart)
                newEntries = [entry - timeDiff for entry in newEntries]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return self.new(entries=newEntries, minTimestamp=minT, maxTimestamp=maxT)

    def dejitter(
        self,
        referenceTier: TextgridTier,
        maxDifference: float = 0.001,
    ) -> "IntervalTier":
        """
        Set timestamps in this tier to be the same as values in the reference tier.

        Timestamps will only be moved if they are less than maxDifference away from the
        reference time.

        This can be used to correct minor alignment errors between tiers, as made when
        annotating files manually, etc.

        Args:
            referenceTier: the IntervalTier or PointTier to use as a reference
            maxDifference: the maximum amount to allow timestamps to be moved by

        Returns:
            the modified version of the current tier
        """
        referenceTimestamps = referenceTier.timestamps

        newEntries: List[Interval] = []
        for start, end, label in self.entries:
            startCompare = min(referenceTimestamps, key=lambda x: abs(x - start))
            endCompare = min(referenceTimestamps, key=lambda x: abs(x - end))
            if my_math.lessThanOrEqual(abs(start - startCompare), maxDifference):
                start = startCompare
            if my_math.lessThanOrEqual(abs(end - endCompare), maxDifference):
                end = endCompare
            newEntries.append(Interval(start, end, label))

        return self.new(entries=newEntries)

    def difference(self, tier: "IntervalTier") -> "IntervalTier":
        """Take the set difference of this tier and the given one.

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
        """Modify all timestamps by a constant amount.

        Args:
            offset: the amount to shift all intervals
            reportingMode: Determines the behavior if an entries moves outside
                of minTimestamp or maxTimestamp after being edited

        Returns:
            the modified version of the current tier

        Raises:
            WrongOption: the reportingMode is not valid
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        newEntries: List[Interval] = []
        for start, end, label in self.entries:
            newStart = start + offset
            newEnd = end + offset

            utils.checkIsUndershoot(newStart, self.minTimestamp, errorReporter)
            utils.checkIsOvershoot(newEnd, self.maxTimestamp, errorReporter)

            if newEnd <= 0:
                continue
            if newStart < 0:
                newStart = 0

            newEntries.append(Interval(newStart, newEnd, label))

        return IntervalTier(self.name, newEntries, self.minTimestamp, self.maxTimestamp)

    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> "IntervalTier":
        """Make a region in a tier blank (remove all contained entries).

        Args:
            start:
            end:
            collisionMode: Determines the behavior when the region to erase
                overlaps with existing intervals.
                - 'truncate' partially contained entries will have the portion
                    removed that overlaps with the target entry
                - 'categorical' all entries that overlap, even partially, with
                    the target entry will be completely removed
                - 'error' if the interval to delete overlaps with any entry,
                    raises 'CollisionError'
            doShrink: If True, moves leftward by (/end/ - /start/)
                amount, each item that occurs after /end/

        Returns:
            The modified version of the current tier

        Raises:
            CollisionError: potentially raised if the interval to remove overlaps with
                            an existing interval
            WrongOption: the collisionMode is not valid
        """
        utils.validateOption("collisionMode", collisionMode, constants.EraseCollision)

        matchList = self.crop(start, end, constants.CropCollision.LAX, False).entries
        newTier = self.new()

        if matchList:
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

        if doShrink:
            diff = end - start
            newEntries: List[Interval] = []
            for interval in newTier.entries:
                if interval.end <= start:
                    newEntries.append(interval)
                elif interval.start >= end:
                    newEntries.append(interval - diff)

            # Special case: an interval that spanned the deleted
            # section
            for i in range(0, len(newEntries) - 1):
                rightEdge = newEntries[i].end == start
                leftEdge = newEntries[i + 1].start == start
                sameLabel = newEntries[i].label == newEntries[i + 1].label
                if rightEdge and leftEdge and sameLabel:
                    newInterval = Interval(
                        newEntries[i].start,
                        newEntries[i + 1].end,
                        newEntries[i].label,
                    )

                    newEntries.pop(i + 1)
                    newEntries.pop(i)
                    newEntries.insert(i, newInterval)

                    # Only one interval can span the deleted section,
                    # so if we've found it, move on
                    break

            newTier = newTier.new(entries=newEntries, maxTimestamp=newTier.maxTimestamp - diff)

        return newTier

    def getValuesInIntervals(
        self, dataTupleList: Iterable[Tuple[float, ...]]
    ) -> List[Tuple[Interval, List[Tuple[float, ...]]]]:
        """Return data from dataTupleList contained in labeled intervals.

        Each labeled interval will get its own list of data values.

        dataTupleList should be of the form:
        [(time1, value1a, value1b,...), (time2, value2a, value2b...), ...]
        """

        returnList: List[Tuple[Interval, List[Tuple[float, ...]]]] = []

        for interval in self.entries:
            intervalDataList = utils.getValuesInInterval(
                dataTupleList, interval.start, interval.end
            )
            returnList.append((interval, intervalDataList))

        return returnList

    def getNonEntries(self) -> List[Interval]:
        """Return the regions of the textgrid without labels.

        This can include unlabeled segments and regions marked as silent.
        """
        entries = self.entries
        invertedEntries = [
            Interval(entries[i].end, entries[i + 1].start, "")
            for i in range(len(entries) - 1)
        ]

        # Remove entries that have no duration (ie lie between two entries
        # that share a border)
        invertedEntries = [
            interval for interval in invertedEntries if interval.start < interval.end
        ]

        if entries[0].start > 0:
            invertedEntries.insert(0, Interval(0, entries[0].start, ""))

        if entries[-1].end < self.maxTimestamp:
            invertedEntries.append(Interval(entries[-1].end, self.maxTimestamp, ""))

        return self._homogenizeEntries(invertedEntries, sort=False)

    def insertEntry(
        self,
        entry: Sequence[Any],
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:
        """Insert an interval into the tier.

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

        Raises:
            CollisionError: potentially raised if the interval to insert overlaps with
                            an existing interval
            WrongOption: the collisionMode or collisionReportingMode is not valid
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

        interval = Interval.build(entry)

        matchList = self.crop(
            interval.start, interval.end, constants.CropCollision.LAX, False
        )._entries

        if not matchList:
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
                f"Attempted to insert interval {interval} into tier {self.name} "
                "of textgrid but overlapping entries "
                + " ".join(map(str, matchList))
                + " already exist"
            )

        self.sort()
        self.minTimestamp, self.maxTimestamp = self._calculateMinAndMaxTime(
            minT=self.minTimestamp, maxT=self.maxTimestamp
        )

        if matchList:
            collisionReporter(
                errors.CollisionError,
                f"Collision warning for {interval} with items {matchList} of tier {self.name!r}"
            )

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionMode: Literal["stretch", "split", "no_change", "error"],
    ) -> "IntervalTier":
        """Insert a blank region into the tier.

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

        Raises:
            CollisionError: potentially raised if the interval to insert overlaps with
                            an existing interval
            WrongOption: the collisionMode is not valid
        """
        utils.validateOption(
            "collisionMode", collisionMode, constants.WhitespaceCollision
        )

        newEntries: List[Interval] = []
        for interval in self.entries:
            # Entry exists before the insertion point
            if interval.end <= start:
                newEntries.append(interval)
            # Entry exists after the insertion point
            elif interval.start >= start:
                newEntries.append(interval + duration)
            # Entry straddles the insertion point
            elif interval.start <= start and interval.end > start:
                if collisionMode == constants.WhitespaceCollision.STRETCH:
                    newEntries.append(
                        Interval(
                            interval.start, interval.end + duration, interval.label
                        )
                    )
                elif collisionMode == constants.WhitespaceCollision.SPLIT:
                    # Left side of the split
                    newEntries.append(Interval(interval.start, start, interval.label))
                    # Right side of the split, shifted by duration
                    newEntries.append(Interval(start, interval.end, interval.label) + duration)
                elif collisionMode == constants.WhitespaceCollision.NO_CHANGE:
                    newEntries.append(interval)
                else:
                    raise errors.CollisionError(
                        f"Collision occured during insertSpace() for interval {interval} "
                        f"and given white space insertion interval ({start}, {start + duration})"
                    )

        newTier = self.new(
            entries=newEntries, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def intersection(self, tier: "IntervalTier", demarcator: str = "-") -> "IntervalTier":
        """Take the set intersection of this tier and the given one.

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
        retEntries: List[Interval] = []
        for interval in tier.entries:
            subTier = self.crop(
                interval.start, interval.end, constants.CropCollision.TRUNCATED, False
            )

            # Combine the labels in the two tiers
            subEntries = [
                Interval(
                    subInterval.start,
                    subInterval.end,
                    f"{subInterval.label}{demarcator}{interval.label}",
                )
                for subInterval in subTier.entries
            ]

            retEntries.extend(subEntries)

        return self.new(f"{self.name}-{tier.name}", retEntries)

    def mergeLabels(self, tier: "IntervalTier", demarcator: str = ",") -> "IntervalTier":
        """Merge labels of overlapping tiers into this tier.

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
        retEntries: List[Interval] = []
        for interval in self.entries:
            subTier = tier.crop(
                interval.start, interval.end, constants.CropCollision.TRUNCATED, False
            )
            if not subTier._entries:
                continue

            subLabel = demarcator.join([entry.label for entry in subTier.entries])
            label = f"{interval.label}({subLabel})"

            start = min(interval.start, subTier._entries[0].start)
            end = max(interval.end, subTier._entries[-1].end)

            retEntries.append(Interval(start, end, label))

        return self.new(f"{self.name}-{tier.name}", retEntries)

    def morph(
        self,
        targetTier: "IntervalTier",
        filterFunc: Optional[Callable[[str], bool]] = None,
    ) -> "IntervalTier":
        """Morph the duration of segments in this tier to those in another.

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
        newEntries: List[Interval] = []
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

            newEntries.append(Interval(newStart, newEnd, sourceInterval.label))

        newMin = self.minTimestamp
        cumulativeDifference = newEntries[-1].end - self.entries[-1].end
        newMax = self.maxTimestamp + cumulativeDifference

        return self.new(entries=newEntries, minTimestamp=newMin, maxTimestamp=newMax)

    def toZeroCrossings(self, wavFN: str) -> "IntervalTier":
        """Move all timestamps to the nearest zero crossing."""
        wav = audio.QueryWav(wavFN)

        intervals: List[Interval] = []
        for start, end, label in self.entries:
            newStart = wav.findNearestZeroCrossing(start)
            newStop = wav.findNearestZeroCrossing(end)
            intervals.append(Interval(newStart, newStop, label))

        return self.new(entries=intervals)

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """Validate this tier.

        Args:
            reportingMode (str): Determines the behavior if validation fails.

        Returns:
            True if the tier is valid; False if not

        Raises:
            WrongOption: the reportingMode is not valid
            TextgridStateError: potentially raised when the textgrid is not valid
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
                    f"Invalid interval. End time occurs before or on the start time: {interval}",
                )

            if previousInterval and previousInterval.end > interval.start:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Intervals are not sorted in time: "
                    f"{previousInterval} and {interval}",
                )

            if utils.checkIsUndershoot(interval.start, self.minTimestamp, errorReporter):
                isValid = False

            if utils.checkIsOvershoot(interval.end, self.maxTimestamp, errorReporter):
                isValid = False

            previousInterval = interval

        return isValid
