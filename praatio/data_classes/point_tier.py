"""
A PointTier is a tier containing an array of points -- data that exists at a specific point in time
"""
from typing import (
    List,
    Tuple,
    Optional,
    Any,
)

from typing_extensions import Literal

from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils

from praatio.data_classes import textgrid_tier


class PointTier(textgrid_tier.TextgridTier):

    tierType = constants.POINT_TIER
    entryType = constants.Point

    def __init__(
        self,
        name: str,
        entryList: List[constants.Point],
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

        entryList = [constants.Point(float(time), label) for time, label in entryList]

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
        mode: Literal["strict", "lax", "truncated"] = "lax",
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
        if cropStart >= cropEnd:
            raise errors.ArgumentError(
                f"Crop error: start time ({cropStart}) must occur before end time ({cropEnd})"
            )

        newEntryList = []

        for entry in self.entryList:
            timestamp = entry.time

            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntryList.append(entry)

        if rebaseToZero is True:
            newEntryList = [
                constants.Point(timeV - cropStart, label)
                for timeV, label in newEntryList
            ]
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        return PointTier(self.name, newEntryList, minT, maxT)

    def deleteEntry(self, entry: constants.Point) -> None:
        """Removes an entry from the entryList"""
        self.entryList.pop(self.entryList.index(entry))

    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "PointTier":
        """
        Modifies all timestamps by a constant amount

        Args:
            offset (float):
            reportingMode (str): one of "silence", "warning", or "error". This flag
                determines the behavior if an entries moves outside of minTimestamp
                or maxTimestamp after being edited

        Returns:
            PointTier: the modified version of the current tier
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        newEntryList: List[constants.Point] = []
        for timestamp, label in self.entryList:

            newTimestamp = timestamp + offset
            utils.checkIsUndershoot(newTimestamp, self.minTimestamp, errorReporter)
            utils.checkIsOvershoot(newTimestamp, self.maxTimestamp, errorReporter)

            if newTimestamp < 0:
                continue

            newEntryList.append(constants.Point(newTimestamp, label))

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
    ) -> List[Tuple[Any, ...]]:
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

        It returns the data in the form of
        [(t1, v1a, v1b, ..), (t2, v2a, v2b), ..]

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
        """
        Makes a region in a tier blank (removes all contained entries)

        Args:
            start (float): the start of the deletion interval
            end (float): the end of the deletion interval
            collisionMode (str): Ignored for the moment (added for compatibility with
                eraseRegion() for Interval Tiers)
            doShrink (bool): if True, moves leftward by (/end/ - /start/) all points
                to the right of /end/

        Returns:
            PointTier: the modified version of the current tier
        """

        newTier = self.new()
        croppedTier = newTier.crop(start, end, constants.CropCollision.TRUNCATED, False)
        matchList = croppedTier.entryList

        if len(matchList) > 0:
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
                    newEntryList.append(constants.Point(point.time - diff, point.label))

            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList, maxTimestamp=newMax)

        return newTier

    def insertEntry(
        self,
        entry: constants.Point,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:
        """
        inserts an interval into the tier

        Args:
            entry (tuple|Point): the entry to insert
            warnFlag (bool): see below for details
            collisionMode (str): determines the behavior if intervals exist in
                the insertion area. One of ('replace', 'merge', or None)
                - 'replace', existing items will be removed
                - 'merge', inserting item will be fused with existing items
                - 'error', will throw TextgridCollisionException

        Returns:
            None

        If warnFlag is True and collisionMode is not None, the user is notified
        of each collision
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

        if not isinstance(entry, constants.Point):
            newPoint = constants.Point(entry[0], entry[1])
        else:
            newPoint = entry

        matchList = []
        i = None
        for i, point in enumerate(self.entryList):
            if point.time == newPoint.time:
                matchList.append(point)
                break

        if len(matchList) == 0:
            self.entryList.append(newPoint)

        elif collisionMode == constants.IntervalCollision.REPLACE:
            self.deleteEntry(self.entryList[i])
            self.entryList.append(newPoint)

        elif collisionMode == constants.IntervalCollision.MERGE:
            oldPoint = self.entryList[i]
            mergedPoint = constants.Point(
                newPoint.time, "-".join([oldPoint.label, newPoint.label])
            )
            self.deleteEntry(self.entryList[i])
            self.entryList.append(mergedPoint)

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
        """
        Inserts a region into the tier

        Args:
            start (float): the start time to insert a space at
            duration (float): the duration of the space to insert
            collisionMode (str): Ignored for the moment (added for compatibility
                with insertSpace() for Interval Tiers)

        Returns:
            PointTier: the modified version of the current tier
        """

        newEntryList = []
        for point in self.entryList:
            if point.time <= start:
                newEntryList.append(point)
            elif point.time > start:
                newEntryList.append(constants.Point(point.time + duration, point.label))

        newTier = self.new(
            entryList=newEntryList, maxTimestamp=self.maxTimestamp + duration
        )

        return newTier

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """
        Validate this tier

        Returns whether the tier is valid or not. If reportingMode is "warning"
        or "error" this will also print on error or stop execution, respectively.

        Args:
            reportingMode (str): one of "silence", "warning", or "error". This flag
                determines the behavior if there is a size difference between the
                maxTimestamp in the tier and the current textgrid.

        Returns:
            bool
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        isValid = True
        previousPoint = None
        for point in self.entryList:
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
