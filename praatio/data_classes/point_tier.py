"""
A PointTier is a tier containing an array of points -- data that exists at a specific point in time
"""
from typing import List, Tuple, Optional, Any, Sequence

from typing_extensions import Literal

from praatio.utilities.constants import (
    Point,
    POINT_TIER,
)
from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils

from praatio.data_classes import textgrid_tier


def _homogenizeEntries(entries):
    """
    Enforces consistency in points

    - converts all entries to points
    - removes whitespace in labels
    - sorts values by time
    """
    processedEntries = [Point(float(time), label.strip()) for time, label in entries]
    processedEntries.sort()
    return processedEntries


def _calculateMinAndMaxTime(entries: Sequence[Point], minT=None, maxT=None):
    timeList = [time for time, label in entries]
    if minT is not None:
        timeList.append(float(minT))
    if maxT is not None:
        timeList.append(float(maxT))

    try:
        calculatedMinT = min(timeList)
        calculatedMaxT = max(timeList)
    except ValueError:
        raise errors.TimelessTextgridTierException()

    return (calculatedMinT, calculatedMaxT)


class PointTier(textgrid_tier.TextgridTier):

    tierType = POINT_TIER
    entryType = Point

    def __init__(
        self,
        name: str,
        entries: List[Point],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):
        """A point tier is for annotating instaneous events

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

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"] = "lax",
        rebaseToZero: bool = True,
    ) -> "PointTier":
        """Creates a new tier containing all entries inside the new interval

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

        newEntries = []

        for entry in self.entries:
            timestamp = entry.time

            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntries.append(entry)

        if rebaseToZero is True:
            newEntries = [
                Point(timeV - cropStart, label) for timeV, label in newEntries
            ]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return PointTier(self.name, newEntries, minT, maxT)

    def deleteEntry(self, entry: Point) -> None:
        """Removes an entry from the entries"""
        self._entries.pop(self._entries.index(entry))

    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "PointTier":
        """Modifies all timestamps by a constant amount

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
        dataTupleList: List[Tuple[float, ...]],
        fuzzyMatching: bool = False,
    ) -> List[Tuple[Any, ...]]:
        """Get the values that occur at points in the point tier

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
        retList = []

        sortedDataTupleList = sorted(dataTupleList)
        for timestamp, label in self.entries:
            retTuple = utils.getValueAtTime(
                timestamp,
                sortedDataTupleList,
                fuzzyMatching=fuzzyMatching,
                startI=currentIndex,
            )
            retRow, currentIndex = retTuple
            retList.append(retRow)

        return retList

    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> "PointTier":
        """Makes a region in a tier blank (removes all contained entries)

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

        if len(matchList) > 0:
            # Remove all the matches from the entries
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for point in matchList[::-1]:
                newTier.deleteEntry(point)

        if doShrink is True:
            newEntries = []
            diff = end - start
            for point in newTier.entries:
                if point.time < start:
                    newEntries.append(point)
                elif point.time > end:
                    newEntries.append(Point(point.time - diff, point.label))

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entries=newEntries, maxTimestamp=newMax)

        return newTier

    def insertEntry(
        self,
        entry: Point,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:
        """Inserts an interval into the tier

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

        matchList = []
        i = None
        for i, point in enumerate(self.entries):
            if point.time == newPoint.time:
                matchList.append(point)
                break

        if len(matchList) == 0:
            self._entries.append(newPoint)

        elif collisionMode == constants.IntervalCollision.REPLACE:
            self.deleteEntry(self.entries[i])
            self._entries.append(newPoint)

        elif collisionMode == constants.IntervalCollision.MERGE:
            oldPoint = self.entries[i]
            mergedPoint = Point(
                newPoint.time, "-".join([oldPoint.label, newPoint.label])
            )
            self.deleteEntry(self._entries[i])
            self._entries.append(mergedPoint)

        else:
            raise errors.CollisionError(
                f"Attempted to insert interval {point} into tier {self.name} "
                "of textgrid but overlapping entries "
                f"{[tuple(interval) for interval in matchList]} "
                "already exist"
            )

        self.sort()

        if len(matchList) != 0:
            collisionReporter(
                errors.CollisionError,
                f"Collision warning for ({point}) with items ({matchList}) of tier '{self.name}'",
            )

    def insertSpace(
        self,
        start: float,
        duration: float,
        _collisionMode: Literal["stretch", "split", "no_change", "error"] = "error",
    ) -> "PointTier":
        """Inserts a region into the tier

        Args:
            start: the start time to insert a space at
            duration: the duration of the space to insert
            collisionMode: Ignored for the moment (added for compatibility
                with insertSpace() for Interval Tiers)

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntries = []
        for point in self.entries:
            if point.time <= start:
                newEntries.append(point)
            elif point.time > start:
                newEntries.append(Point(point.time + duration, point.label))

        newTier = self.new(
            entries=newEntries, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """Validate this tier

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
