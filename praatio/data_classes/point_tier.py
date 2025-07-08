"""
A PointTier is a tier containing an array of points -- data that exists at a specific point in time.
"""
from typing import List, Tuple, Optional, Iterable, Any

from typing_extensions import Literal

from praatio import audio
from praatio.utilities.constants import Point, POINT_TIER
from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils
from praatio.utilities import my_math

from praatio.data_classes.textgrid_tier import TextgridTier


def _homogenizeEntries(entries: Iterable[Tuple[float, str]]) -> List[Point]:
    """
    Enforce consistency in points.

    - Convert all entries to points.
    - Remove whitespace in labels.
    - Sort values by time.
    """
    processedEntries = [Point(float(time), label.strip()) for time, label in entries]
    processedEntries.sort()
    return processedEntries


def _calculateMinAndMaxTime(
    entries: Iterable[Point],
    minT: Optional[float] = None,
    maxT: Optional[float] = None,
) -> Tuple[float, float]:

    timeList = [time for time, label in entries]
    if minT is not None:
        timeList.append(float(minT))
    if maxT is not None:
        timeList.append(float(maxT))

    try:
        return (min(timeList), max(timeList))
    except ValueError:
        raise errors.TimelessTextgridTierException()


class PointTier(TextgridTier[Point]):
    tierType = POINT_TIER
    entryType = Point

    def __init__(
        self,
        name: str,
        entries: Iterable[Tuple[float, str]],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
        """A point tier is for annotating instaneous events.

        The entries is of the form:
        [(timeVal1, label1), (timeVal2, label2), ]

        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('peak point here') or numerical data e.g. (pitch values
        like '132'))
        """
        entries = _homogenizeEntries(entries)
        calculatedMinT, calculatedMaxT = _calculateMinAndMaxTime(entries, minT, maxT)

        super(PointTier, self).__init__(name, entries, calculatedMinT, calculatedMaxT)

    @property
    def timestamps(self) -> List[float]:
        """All unique timestamps used in this tier."""
        tmpTimestamps = [time for time, _ in self.entries]

        uniqueTimestamps = list(set(tmpTimestamps))
        uniqueTimestamps.sort()

        return uniqueTimestamps

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"] = "lax",
        rebaseToZero: bool = True,
    ) -> "PointTier":
        """Create a new tier containing all entries inside the new interval.

        Args:
            cropStart:
            cropEnd:
            mode: Mode is ignored.  This parameter is kept for
                compatibility with IntervalTier.crop()
            rebaseToZero: if True, all entries will have their
                timestamps subtracted by *cropStart*.

        Returns:
            the modified version of the current tier
        """
        if cropStart >= cropEnd:
            raise errors.ArgumentError(
                f"Crop error: start time ({cropStart}) must occur before end time ({cropEnd})"
            )

        newEntries: List[Point] = []

        for entry in self.entries:
            timestamp = entry.time

            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntries.append(entry)

        if rebaseToZero:
            newEntries = [
                Point(timeV - cropStart, label) for timeV, label in newEntries
            ]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return PointTier(self.name, newEntries, minT, maxT)

    def dejitter(
        self, referenceTier: "PointTier", maxDifference: float = 0.001
    ) -> "PointTier":
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

        newEntries: List[Point] = []
        for time, label in self.entries:
            timeCompare = min(referenceTimestamps, key=lambda x: abs(x - time))

            if my_math.lessThanOrEqual(abs(time - timeCompare), maxDifference):
                time = timeCompare
            newEntries.append(Point(time, label))

        return self.new(entries=newEntries)

    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "PointTier":
        """Modify all timestamps by a constant amount.

        Args:
            offset:
            reportingMode: one of "silence", "warning", or "error". This flag
                determines the behavior if an entries moves outside of minTimestamp
                or maxTimestamp after being edited

        Returns:
            the modified version of the current tier
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        newEntries: List[Point] = []
        for timestamp, label in self.entries:
            newTimestamp = timestamp + offset
            utils.checkIsUndershoot(newTimestamp, self.minTimestamp, errorReporter)
            utils.checkIsOvershoot(newTimestamp, self.maxTimestamp, errorReporter)

            if newTimestamp < 0:
                continue

            newEntries.append(Point(newTimestamp, label))

        # Determine new min and max timestamps
        timeList = [float(point.time) for point in newEntries]
        newMin = min(timeList)
        newMax = max(timeList)

        if newMin > self.minTimestamp:
            newMin = self.minTimestamp

        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp

        return PointTier(self.name, newEntries, newMin, newMax)

    def getValuesAtPoints(
        self,
        dataTupleList: Iterable[Tuple[float, ...]],
        fuzzyMatching: bool = False,
    ) -> List[Tuple[Any, ...]]:
        """Get the values that occur at points in the point tier.

        The procedure assumes that all data is ordered in time.
        dataTupleList should be in the form
        [(t1, v1a, v1b, ..), (t2, v2a, v2b, ..), ..]

        It returns the data in the form of
        [(t1, v1a, v1b, ..), (t2, v2a, v2b), ..]

        The procedure makes one pass through dataTupleList and one
        pass through self.entries.  If the data is not sequentially
        ordered, the incorrect response will be returned.

        Args:
            dataTupleList:
            fuzzyMatching: if True, if there is not a feature value
                at a point, the nearest feature value will be taken.

        Returns:
            A list of values that exist at the given timepoints
        """

        currentIndex = 0
        retList: List[Tuple[Any, ...]] = []

        sortedDataTupleList = sorted(dataTupleList)
        for timestamp, label in self.entries:
            retRow, currentIndex = utils.getValueAtTime(
                timestamp,
                sortedDataTupleList,
                fuzzyMatching=fuzzyMatching,
                startI=currentIndex,
            )
            retList.append(retRow)

        return retList

    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> "PointTier":
        """Make a region in a tier blank (removes all contained entries).

        Args:
            start: the start of the deletion interval
            end: the end of the deletion interval
            collisionMode: Ignored for the moment (added for compatibility with
                eraseRegion() for Interval Tiers)
            doShrink: if True, moves leftward by (/end/ - /start/) all points
                to the right of /end/

        Returns:
            The modified version of the current tier
        """

        newTier = self.new()
        croppedTier = newTier.crop(start, end, constants.CropCollision.TRUNCATED, False)
        matchList = croppedTier.entries

        if matchList:
            # Remove all the matches from the entries
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for point in matchList[::-1]:
                newTier.deleteEntry(point)

        if doShrink:
            newEntries: List[Point] = []
            diff = end - start
            for point in newTier.entries:
                if point.time < start:
                    newEntries.append(point)
                elif point.time > end:
                    newEntries.append(Point(point.time - diff, point.label))

            newTier = newTier.new(entries=newEntries, maxTimestamp=newTier.maxTimestamp - diff)

        return newTier

    def insertEntry(
        self,
        entry: Point,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:
        """Insert an interval into the tier.

        Args:
            entry: the entry to insert
            collisionMode: determines the behavior if intervals exist in
                the insertion area.
                - 'replace', existing items will be removed
                - 'merge', inserting item will be fused with existing items
                - 'error', will throw TextgridCollisionException
            collisionReportingMode:

        Returns:
            None
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

        if not isinstance(entry, Point):
            newPoint = Point(entry[0], entry[1])
        else:
            newPoint = entry

        match = None
        for point in self.entries:
            if point.time == newPoint.time:
                match = point
                break

        if match is None:
            self._entries.append(newPoint)

        elif collisionMode == constants.IntervalCollision.REPLACE:
            self.deleteEntry(match)
            self._entries.append(newPoint)

        elif collisionMode == constants.IntervalCollision.MERGE:
            mergedPoint = Point(
                newPoint.time, match.label + "-" + newPoint.label
            )
            self.deleteEntry(match)
            self._entries.append(mergedPoint)

        else:
            raise errors.CollisionError(
                f"Attempted to insert point {newPoint} into tier {self.name} "
                f"of textgrid but overlapping entry {match} already exists"
            )

        self.sort()

        if match is not None:
            collisionReporter(
                errors.CollisionError,
                f"Collision warning for {newPoint} with items {match} of tier {self.name!r}",
            )

    def insertSpace(
        self,
        start: float,
        duration: float,
        _collisionMode: Literal["stretch", "split", "no_change", "error"] = "error",
    ) -> "PointTier":
        """Insert a region into the tier.

        Args:
            start: the start time to insert a space at
            duration: the duration of the space to insert
            collisionMode: Ignored for the moment (added for compatibility
                with insertSpace() for Interval Tiers)

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntries: List[Point] = []
        for point in self.entries:
            if point.time <= start:
                newEntries.append(point)
            elif point.time > start:
                newEntries.append(Point(point.time + duration, point.label))

        return self.new(entries=newEntries, maxTimestamp=self.maxTimestamp + duration)

    def toZeroCrossings(self, wavFN: str) -> "PointTier":
        """Move all timestamps to the nearest zero crossing."""
        wav = audio.QueryWav(wavFN)

        points: List[Point] = []
        for time, label in self.entries:
            newTime = wav.findNearestZeroCrossing(time)
            points.append(Point(newTime, label))

        return self.new(entries=points)

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """Validate this tier.

        Returns whether the tier is valid or not. If reportingMode is "warning"
        or "error" this will also print on error or stop execution, respectively.

        Args:
            reportingMode: Determines the behavior if there is a size difference
                between the maxTimestamp in the tier and the current textgrid.

        Returns:
            True if this tier is valid; False otherwise
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        isValid = True
        previousPoint = None
        for point in self.entries:
            if previousPoint and previousPoint.time > point.time:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Points are not sorted in time: "
                    f"[({previousPoint}), ({point})]",
                )

            if utils.checkIsUndershoot(point.time, self.minTimestamp, errorReporter):
                isValid = False

            if utils.checkIsOvershoot(point.time, self.maxTimestamp, errorReporter):
                isValid = False

            previousPoint = point

        return isValid
