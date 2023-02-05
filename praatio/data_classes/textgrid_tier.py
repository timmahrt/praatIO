"""
The abstract class used by all textgrid tiers
"""
import re
import copy
import math
from typing import (
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from abc import ABC, abstractmethod

from typing_extensions import Literal


from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils

T = TypeVar("T", bound="TextgridTier")


class TextgridTier(ABC):

    tierType: str
    entryType: Union[Type[constants.Point], Type[constants.Interval]]

    def __init__(
        self,
        name: str,
        entries: List,
        minT: float,
        maxT: float,
        errorMode: Literal["silence", "warning", "error"] = "warning",
    ):
        "A container that stores and operates over interval and point tiers"
        utils.validateOption("errorMode", errorMode, constants.ErrorReportingMode)

        """See PointTier or IntervalTier"""
        entries.sort()

        self.name = name
        self._entries = entries
        self.minTimestamp = minT
        self.maxTimestamp = maxT
        self.errorReporter = utils.getErrorReporter(errorMode)

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        isEqual = True
        isEqual &= self.name == other.name
        isEqual &= math.isclose(self.minTimestamp, other.minTimestamp)
        isEqual &= math.isclose(self.maxTimestamp, other.maxTimestamp)
        isEqual &= len(self.entries) == len(self.entries)

        # TODO: Intervals and Points now use isclose, so we can simplify this
        #       logic (selfEntry == otherEntry); however, this will break
        #       things for klattgrids
        if isEqual:
            for selfEntry, otherEntry in zip(self.entries, other.entries):
                for selfSubEntry, otherSubEntry in zip(selfEntry, otherEntry):
                    try:
                        isEqual &= math.isclose(selfSubEntry, otherSubEntry)
                    except TypeError:
                        isEqual &= selfSubEntry == otherSubEntry

        return isEqual

    @property
    def entries(self):
        return tuple(self._entries)

    def appendTier(self, tier: "TextgridTier") -> "TextgridTier":
        """Append a tier to the end of this one.

        This tier's maxtimestamp will be lengthened by the amount in the passed in tier.
        """
        if self.tierType != tier.tierType:
            raise errors.ArgumentError(
                f"Cannot append a tier of type {type(self)} to a tier of type {type(tier)}."
            )

        maxTime = self.maxTimestamp + tier.maxTimestamp

        # We're increasing the size of the tier, so of course its intervals
        # may exceed the bounds of the tier's maxTimestamp, triggering
        # errors/warnings--we can ignore those
        appendTier = tier.editTimestamps(
            self.maxTimestamp, constants.ErrorReportingMode.SILENCE
        )

        entries = self._entries + appendTier._entries
        entries.sort()

        return self.new(
            self.name, entries, minTimestamp=self.minTimestamp, maxTimestamp=maxTime
        )

    def find(
        self,
        matchLabel: str,
        substrMatchFlag: bool = False,
        usingRE: bool = False,
    ) -> List[int]:
        """Returns the index of all intervals that match the given label

        Args:
            matchLabel: the label to search for
            substrMatchFlag: if True, match any label containing matchLabel.
                if False, label must be the same as matchLabel.
            usingRE: if True, matchLabel is interpreted as a regular expression

        Returns:
            A list of indicies
        """
        returnList = []
        if usingRE is True:
            for i, entry in enumerate(self.entries):
                matchList = re.findall(matchLabel, entry.label, re.I)
                if matchList != []:
                    returnList.append(i)
        else:
            for i, entry in enumerate(self.entries):
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
        entries: Optional[list] = None,
        minTimestamp: Optional[float] = None,
        maxTimestamp: Optional[float] = None,
    ) -> T:
        """Make a new tier derived from the current one"""
        if name is None:
            name = self.name
        if entries is None:
            entries = copy.deepcopy(self.entries)
            entries = [
                self.entryType(*entry)
                if isinstance(entry, tuple) or isinstance(entry, list)
                else entry
                for entry in entries
            ]
        if minTimestamp is None:
            minTimestamp = self.minTimestamp
        if maxTimestamp is None:
            maxTimestamp = self.maxTimestamp
        return type(self)(name, entries, minTimestamp, maxTimestamp)

    def sort(self) -> None:
        """Sorts the entries in the list of entries"""
        # A list containing tuples and lists will be sorted with tuples
        # first and then lists.  To correctly sort, we need to make
        # sure that all data structures inside the entry list are
        # of the same data type.  The entry list is sorted whenever
        # the entry list is modified, so this is probably the best
        # place to enforce the data type
        self._entries = [
            entry if isinstance(entry, self.entryType) else self.entryType(*entry)
            for entry in self.entries
        ]
        self._entries.sort()

    def union(self, tier: "TextgridTier") -> "TextgridTier":
        """The given tier is set unioned to this tier.

        All entries in the given tier are added to the current tier.
        Overlapping entries are merged.
        """
        retTier = self.new()

        for entry in tier.entries:
            retTier.insertEntry(
                entry,
                collisionMode=constants.IntervalCollision.MERGE,
                collisionReportingMode=constants.ErrorReportingMode.SILENCE,
            )

        retTier.sort()

        return retTier

    @abstractmethod
    def editTimestamps(
        self,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> "TextgridTier":  # pragma: no cover
        pass

    @abstractmethod
    def insertEntry(
        self,
        entry,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def eraseRegion(
        self,
        start: float,
        end: float,
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> "TextgridTier":  # pragma: no cover
        pass

    @abstractmethod
    def crop(
        self,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> "TextgridTier":  # pragma: no cover
        pass

    @abstractmethod
    def insertSpace(
        self,
        start: float,
        duration: float,
        collisionMode: Literal["stretch", "split", "no_change", "error"],
    ) -> "TextgridTier":  # pragma: no cover
        pass

    @abstractmethod
    def deleteEntry(self, entry) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def validate(self, reportingMode) -> bool:  # pragma: no cover
        pass
