"""
Functions for reading/writing/manipulating Textgrid classes.

This is the 'heart' of praatio.
"""
import io
import copy
from typing import TYPE_CHECKING, Optional, Tuple, List, Iterable, Any, Union, TypeVar, Generic
from typing_extensions import Literal
from collections import OrderedDict


from praatio.utilities.constants import (
    TextgridFormats,
    MIN_INTERVAL_LENGTH,
    CropCollision,
)

from praatio.data_classes.point_tier import PointTier
from praatio.data_classes.interval_tier import IntervalTier
if TYPE_CHECKING:
    from praatio.data_classes.klattgrid import KlattPointTier, KlattContainerTier
from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import my_math
from praatio.utilities import textgrid_io
from praatio.utilities import utils


# TierType: for defining BaseTextgrid as a generic container class
TierType = TypeVar(
    "TierType", Union[PointTier, IntervalTier], "Union[KlattPointTier, KlattContainerTier]"
)
# GridType: can be replaced with typing.Self in Python 3.11+
GridType = TypeVar("GridType", bound="BaseTextgrid")


class BaseTextgrid(Generic[TierType]):
    """A container that stores and operates over interval and point tiers.

    Textgrids are used by the Praat software to group tiers.  Each tier
    contains different annotation information for an audio recording.

    Attributes:
        tierNames(Tuple[str]): the list of tier names in the textgrid
        tiers(Tuple[TextgridTier]): the list of ordered tiers
        minTimestamp(float): the minimum allowable timestamp in the textgrid
        maxTimestamp(float): the maximum allowable timestamp in the textgrid
    """

    def __init__(self, minTimestamp: Optional[float] = None, maxTimestamp: Optional[float] = None):
        """Constructor for Textgrids.

        Args:
            minTimestamp: the minimum allowable timestamp in the textgrid
            maxTimestamp: the maximum allowable timestamp in the textgrid
        """

        self._tierDict: OrderedDict[str, TierType] = OrderedDict()

        # TODO: Timestamps are determined by the first tier added.
        # But it causes unexpected problems if users call certain methods before adding any tiers.
        # It's better to add checks in those methods.
        self.minTimestamp: float = minTimestamp  # type: ignore[assignment]
        self.maxTimestamp: float = maxTimestamp  # type: ignore[assignment]

    def __len__(self):
        return len(self._tierDict)

    def __iter__(self):
        return iter(self._tierDict.values())

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and my_math.isclose(self.minTimestamp, other.minTimestamp)
            and my_math.isclose(self.maxTimestamp, other.maxTimestamp)
            and self._tierDict == other._tierDict
        )

    def __repr__(self):
        return f"{type(self).__name__}{(list(self.tiers), self.minTimestamp, self.maxTimestamp)}"

    @property
    def tierNames(self) -> Tuple[str, ...]:
        return tuple(self._tierDict.keys())

    @property
    def tiers(self) -> Tuple[TierType, ...]:
        return tuple(self._tierDict.values())

    def addTier(
        self,
        tier: TierType,
        tierIndex: Optional[int] = None,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> None:
        """Add a tier to this textgrid.

        Args:
            tier: The tier to add to the textgrid
            tierIndex: Insert the tier into the specified position;
                if None, the tier will appear after all existing tiers
            reportingMode: This flag determines the behavior if there is a size
                difference between the maxTimestamp in the tier and the current
                textgrid.

        Returns:
            None

        Raises:
            TierNameExistsError: The textgrid already contains a tier with the same
                name as the tier being added
            TextgridStateAutoModified: The minimum or maximum timestamp was changed
                when not permitted
            IndexError: TierIndex is too large for the size of the existing tier list
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        if tier.name in self.tierNames:
            raise errors.TierNameExistsError("Tier name already in tier")

        if tierIndex is None:
            self._tierDict[tier.name] = tier
        else:
            tierNamesAfterThis = tuple(self.tierNames)[tierIndex:]
            # Insert the new tier at the end
            self._tierDict[tier.name] = tier
            # Then move tiers that should be after it in the correct order
            for tierName in tierNamesAfterThis:
                self._tierDict.move_to_end(tierName)

        minV = tier.minTimestamp
        if minV is not None:
            if self.minTimestamp is None:
                self.minTimestamp = minV
            elif minV < self.minTimestamp:
                errorReporter(
                    errors.TextgridStateAutoModified,
                    f"Minimum timestamp in Textgrid changed from ({self.minTimestamp}) to ({minV})",
                )
                self.minTimestamp = minV

        maxV = tier.maxTimestamp
        if maxV is not None:
            if self.maxTimestamp is None:
                self.maxTimestamp = maxV
            elif maxV > self.maxTimestamp:
                errorReporter(
                    errors.TextgridStateAutoModified,
                    f"Maximum timestamp in Textgrid changed from ({self.maxTimestamp}) to ({maxV})",
                )
                self.maxTimestamp = maxV

    def getTier(self, tierName: str) -> TierType:
        """Get the tier with the specified name"""
        return self._tierDict[tierName]

    def new(self: GridType) -> GridType:
        """Return a copy of this Textgrid."""
        return copy.deepcopy(self)

    def renameTier(self, oldName: str, newName: str) -> None:
        oldTier = self.getTier(oldName)
        tierIndex = self.tierNames.index(oldName)
        self.removeTier(oldName)
        self.addTier(oldTier.new(newName, oldTier.entries), tierIndex)  # type: ignore

    def removeTier(self, name: str) -> TierType:
        return self._tierDict.pop(name)

    def replaceTier(
        self,
        name: str,
        newTier: TierType,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> None:
        tierIndex = self.tierNames.index(name)
        self.removeTier(name)
        self.addTier(newTier, tierIndex, reportingMode)


class Textgrid(BaseTextgrid[Union[PointTier, IntervalTier]]):
    def appendTextgrid(self, tg: "Textgrid", onlyMatchingNames: bool) -> "Textgrid":
        """Append one textgrid to the end of this one.

        Args:
            tg: the textgrid to add to this one
            onlyMatchingNames: if False, tiers that don't appear in both
                textgrids will also appear

        Returns:
            the modified version of the current textgrid
        """
        minTime = self.minTimestamp
        maxTime = self.maxTimestamp + tg.maxTimestamp
        retTG = Textgrid(minTime, maxTime)

        # Get all tier names.  Ordered first by this textgrid and
        # then by the other textgrid.
        combinedTierNames = list(self.tierNames)
        for tierName in tg.tierNames:
            if tierName not in combinedTierNames:
                combinedTierNames.append(tierName)

        # Determine the tier names that will be in the final textgrid
        finalTierNames: List[str] = []
        if not onlyMatchingNames:
            finalTierNames = combinedTierNames
        else:
            for tierName in combinedTierNames:
                if tierName in self.tierNames:
                    if tierName in tg.tierNames:
                        finalTierNames.append(tierName)

        # Add tiers from this textgrid
        for tierName in finalTierNames:
            if tierName in self.tierNames:
                tier = self.getTier(tierName)
                retTG.addTier(tier)

        # Add tiers from the given textgrid
        for tierName in finalTierNames:
            if tierName in tg.tierNames:
                appendTier = tg.getTier(tierName)
                appendTier = appendTier.new(minTimestamp=minTime, maxTimestamp=maxTime)

                appendTier = appendTier.editTimestamps(self.maxTimestamp)

                if tierName in retTG.tierNames:
                    tier = retTG.getTier(tierName)
                    newEntries = list(retTG.getTier(tierName).entries)
                    newEntries.extend(appendTier.entries)
                    tier = tier.new(
                        entries=newEntries,
                        minTimestamp=minTime,
                        maxTimestamp=maxTime,
                    )
                    retTG.replaceTier(tierName, tier)

                else:
                    tier = appendTier.new(minTimestamp=minTime, maxTimestamp=maxTime)
                    retTG.addTier(tier)

        return retTG

    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "Textgrid":
        """Create a textgrid where all intervals fit within the crop region.

        Args:
            cropStart: The start time of the crop interval
            cropEnd: The stop time of the crop interval
            mode: Determines the crop behavior
                - 'strict', only intervals wholly contained by the crop
                    interval will be kept
                - 'lax', partially contained intervals will be kept
                - 'truncated', partially contained intervals will be
                    truncated to fit within the crop region.
            rebaseToZero: if True, the cropped textgrid timestamps will be
                subtracted by the cropStart; if False, timestamps will not
                be changed

        Returns:
            the modified version of the current textgrid
        """
        utils.validateOption("mode", mode, CropCollision)

        if cropStart >= cropEnd:
            raise errors.ArgumentError(
                f"Crop error: start time ({cropStart}) must occur before end time ({cropEnd})"
            )

        if rebaseToZero:
            minT = 0.0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd
        newTG = Textgrid(minT, maxT)

        for tierName in self.tierNames:
            tier = self.getTier(tierName)
            newTier = tier.crop(cropStart, cropEnd, mode, rebaseToZero)

            reportingMode: Literal[
                "silence", "warning", "error"
            ] = constants.ErrorReportingMode.WARNING
            if mode == constants.CropCollision.LAX:
                # We expect that there will be changes to the size
                # of the textgrid when the mode is LAX
                reportingMode = constants.ErrorReportingMode.SILENCE

            newTG.addTier(newTier, reportingMode=reportingMode)

        return newTG

    def eraseRegion(self, start: float, end: float, doShrink: bool) -> "Textgrid":
        """Make a region in a tier blank (removes all contained entries).

        Intervals that span the region to erase will be truncated.

        Args:
            start:
            end:
            doShrink: if True, all entries appearing after the
                erased interval will be shifted to fill the void (ie
                the duration of the textgrid will be reduced by
                *start* - *end*)

        Returns:
            the modified version of the current textgrid

        Raises:
            ArgumentError
        """
        if start >= end:
            raise errors.ArgumentError(
                f"EraseRegion error: start time ({start}) must occur before end time ({end})"
            )

        diff = end - start

        maxTimestamp = self.maxTimestamp
        if doShrink:
            maxTimestamp -= diff

        newTG = Textgrid(self.minTimestamp, self.maxTimestamp)
        for tier in self.tiers:
            shrunkTier = tier.eraseRegion(
                start, end, constants.EraseCollision.TRUNCATE, doShrink
            )
            newTG.addTier(shrunkTier)

        newTG.maxTimestamp = maxTimestamp

        return newTG

    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "Textgrid":
        """Modify all timestamps by a constant amount.

        Args:
            offset: the amount to offset in seconds
            reportingMode: one of "silence", "warning", or "error". This flag
                determines the behavior if there is a size difference between the
                maxTimestamp in the tier and the current textgrid.

        Returns:
            Textgrid: the modified version of the current textgrid
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )

        tg = Textgrid(self.minTimestamp, self.maxTimestamp)
        for tier in self.tiers:
            if tier.entries:
                tier = tier.editTimestamps(offset, reportingMode)

            tg.addTier(tier, reportingMode=reportingMode)

        return tg

    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionMode: Literal["stretch", "split", "no_change", "error"] = "error",
    ) -> "Textgrid":
        """Insert a blank region into a textgrid.

        Every item that occurs after *start* will be pushed back by
        *duration* seconds

        Args:
            start:
            duration:
            collisionMode: Determines behavior in the event that an
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
        utils.validateOption(
            "collisionMode", collisionMode, constants.WhitespaceCollision
        )

        newTG = Textgrid(self.minTimestamp, self.maxTimestamp)
        newTG.minTimestamp = self.minTimestamp
        newTG.maxTimestamp = self.maxTimestamp + duration

        for tier in self.tiers:
            newTier = tier.insertSpace(start, duration, collisionMode)
            newTG.addTier(newTier)

        return newTG

    def mergeTiers(
        self, tierNames: Optional[Iterable[str]] = None, preserveOtherTiers: bool = True
    ) -> "Textgrid":
        """Combine tiers.

        Args:
            tierList: A list of tier names to combine. If none, combine
                all tiers.
            preserveOtherTiers: If false, uncombined tiers are not
                included in the output.

        Returns:
            Textgrid: the modified version of the current textgrid
        """
        if tierNames is None:
            tierNames = self.tierNames

        # Merge interval tiers and point tiers respectively
        intervalTier = None
        pointTier = None
        for tierName in tierNames:
            tier = self.getTier(tierName)
            if isinstance(tier, IntervalTier):
                intervalTier = intervalTier.union(tier) if intervalTier is not None else tier
            elif isinstance(tier, PointTier):
                pointTier = pointTier.union(tier) if pointTier is not None else tier

        # Create the final textgrid to output
        tg = Textgrid(self.minTimestamp, self.maxTimestamp)

        if preserveOtherTiers:
            for tier in self.tiers:
                if tier.name not in tierNames:
                    tg.addTier(tier)

        if intervalTier is not None:
            tg.addTier(intervalTier)

        if pointTier is not None:
            tg.addTier(pointTier)

        return tg

    def save(
        self,
        fn: str,
        format: Literal["short_textgrid", "long_textgrid", "json", "textgrid_json"],
        includeBlankSpaces: bool,
        minTimestamp: Optional[float] = None,
        maxTimestamp: Optional[float] = None,
        minimumIntervalLength: float = MIN_INTERVAL_LENGTH,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> None:
        """Save the current textgrid to a file.

        Args:
            fn: the fullpath filename of the output
            format: one of ['short_textgrid', 'long_textgrid', 'json', 'textgrid_json']
                'short_textgrid' and 'long_textgrid' are both used by praat
                'json' and 'textgrid_json' are two json variants. 'json' cannot represent
                tiers with different min and max timestamps than the textgrid.
            includeBlankSpaces: if True, blank sections in interval
                tiers will be filled in with an empty interval
                (with a label of ""). If you are unsure, True is recommended
                as Praat needs blanks to render textgrids properly.
            minTimestamp: the minTimestamp of the saved Textgrid;
                if None, use whatever is defined in the Textgrid object.
                If minTimestamp is larger than timestamps in your textgrid,
                an exception will be thrown.
            maxTimestamp: the maxTimestamp of the saved Textgrid;
                if None, use whatever is defined in the Textgrid object.
                If maxTimestamp is smaller than timestamps in your textgrid,
                an exception will be thrown.
            minimumIntervalLength: any labeled intervals smaller
                than this will be removed, useful for removing ultrashort
                or fragmented intervals; if None, don't remove any.
                Removed intervals are merged (without their label) into
                adjacent entries.
            reportingMode: one of "silence", "warning", or "error". This flag
                determines the behavior if there is a size difference between the
                maxTimestamp in the tier and the current textgrid.

        Returns:
            a string representation of the textgrid
        """

        utils.validateOption("format", format, TextgridFormats)
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )

        self.validate(reportingMode)

        tgAsDict = _tgToDictionary(self)

        textgridStr = textgrid_io.getTextgridAsStr(
            tgAsDict,
            format,
            includeBlankSpaces,
            minTimestamp,
            maxTimestamp,
            minimumIntervalLength,
        )

        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(textgridStr)

    def validate(
        self, reportingMode: Literal["silence", "warning", "error"] = "warning"
    ) -> bool:
        """Validate this textgrid.

        Returns whether the textgrid is valid or not. If reportingMode is "warning"
        or "error" this will also print on error or stop execution, respectively.

        Args:
            reportingMode: one of "silence", "warning", or "error". This flag
                determines the behavior if there is a size difference between the
                maxTimestamp in a tier and the current textgrid.

        Returns:
            True if this Textgrid is valid; False if not

        Raises:
            TierNameExistsError: Two tiers have the same name
            TextgridStateError: A timestamp fall outside of the allowable range
        """
        utils.validateOption(
            "reportingMode", reportingMode, constants.ErrorReportingMode
        )
        errorReporter = utils.getErrorReporter(reportingMode)

        isValid = True
        if len(self.tierNames) != len(set(self.tierNames)):
            isValid = False
            errorReporter(
                errors.TierNameExistsError,
                f"Tier names not unique: {self.tierNames}",
            )

        for tier in self.tiers:
            if self.minTimestamp != tier.minTimestamp:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Textgrid has a min timestamp of ({self.minTimestamp}) "
                    f"but tier has ({tier.minTimestamp})",
                )

            if self.maxTimestamp != tier.maxTimestamp:
                isValid = False
                errorReporter(
                    errors.TextgridStateError,
                    f"Textgrid has a max timestamp of ({self.maxTimestamp}) "
                    f"but tier has ({tier.maxTimestamp})",
                )

            isValid = isValid and tier.validate(reportingMode)

        return isValid


def _tgToDictionary(tg: Textgrid) -> dict:
    tiers: List[dict] = []
    for tier in tg.tiers:
        tiers.append({
            "class": tier.tierType,
            "name": tier.name,
            "xmin": tier.minTimestamp,
            "xmax": tier.maxTimestamp,
            "entries": tier.entries,
        })

    return {"xmin": tg.minTimestamp, "xmax": tg.maxTimestamp, "tiers": tiers}
