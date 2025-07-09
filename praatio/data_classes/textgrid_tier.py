"""The abstract class used by all textgrid tiers."""
import re
import math
from typing import List, Optional, Sequence, Type, TypeVar, Iterable, Any, Generic, Tuple
from abc import ABC, abstractmethod

from typing_extensions import Literal

from praatio.utilities import constants
from praatio.utilities import errors
from praatio.utilities import utils


# EntryType: for defining TextgridTier as a generic container class
EntryType = TypeVar("EntryType", constants.Point, constants.Interval, constants.KlattPoint)
# KlattPoint doesn't have a label, making some methods not applicable, so we need another variable
TextgridEntryType = TypeVar("TextgridEntryType", constants.Point, constants.Interval)
# TierType: can be replaced with typing.Self in Python 3.11+
TierType = TypeVar("TierType", bound="TextgridTier")


class TextgridTier(ABC, Generic[EntryType]):
    """A container that stores and operates over interval and point tiers."""
    tierType: str
    entryType: Type[EntryType]

    def __init__(
        self,
        name: str,
        entries: Iterable[Sequence[Any]] = [],
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
        errorMode: Literal["silence", "warning", "error"] = "warning",
    ):
        """
        PointTier entries: [(timeVal1, label1), (timeVal2, label2), ...]
        IntervalTier entries: [(startTime1, endTime1, label1), (startTime2, endTime2, label2), ...]

        The data stored in the labels can be anything but will be interpreted as
        text by praatio. Labels could be descriptive text (e.g. 'peak point here')
        or numerical data (e.g. pitch values like '132').

        The constructor copies all entries, converts them to the proper entry type,
        sorts the entries, and expands the minT and maxT to accommodate all timestamps.
        """
        utils.validateOption("errorMode", errorMode, constants.ErrorReportingMode)
        self.name = name
        self._entries = self._homogenizeEntries(entries)
        self.minTimestamp, self.maxTimestamp = self._calculateMinAndMaxTime(minT=minT, maxT=maxT)
        self.errorReporter = utils.getErrorReporter(errorMode)

    def new(
        self: TierType,
        name: Optional[str] = None,
        entries: Optional[Iterable[Sequence[Any]]] = None,
        minTimestamp: Optional[float] = None,
        maxTimestamp: Optional[float] = None,
    ) -> TierType:
        """
        Derive a new tier from an existing tier.

        Also copies, converts and sorts all entries, and expands the minT
        and maxT like the __init__ constructor.
        """
        if name is None:
            name = self.name
        if entries is None:
            entries = self._entries
        if minTimestamp is None:
            minTimestamp = self.minTimestamp
        if maxTimestamp is None:
            maxTimestamp = self.maxTimestamp
        return type(self)(name, entries, minTimestamp, maxTimestamp)

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and self.name == other.name
            and math.isclose(self.minTimestamp, other.minTimestamp)
            and math.isclose(self.maxTimestamp, other.maxTimestamp)
            and self._entries == other._entries
        )

    def __repr__(self):
        return type(self).__name__ + \
            f"{(self.name, self._entries, self.minTimestamp, self.maxTimestamp)}"

    @property
    def entries(self) -> Tuple[EntryType, ...]:
        return tuple(self._entries)

    @property
    @abstractmethod
    def timestamps(self) -> List[float]:  # pragma: no cover
        """All unique timestamps used in entries, sorted, not including minT and maxT of the tier."""
        pass

    @classmethod
    def _homogenizeEntries(
        cls,
        entries: Iterable[Sequence[Any]],
        sort: bool = True,
    ) -> List[EntryType]:
        """
        Enforce consistency in entries.

        - Copy and convert all entries to entryType.
        - Strip whitespace in labels.
        - Sort entries by time.
        """
        processedEntries = [cls.entryType.build(entry) for entry in entries]
        if sort:
            processedEntries.sort()
        return processedEntries

    def sort(self) -> None:
        """
        Enforce consistency in self._entries inplace.

        - Copy and convert all entries to entryType.
        - Strip whitespace in labels.
        - Sort entries by time.
        """
        # A list containing tuples and lists will be sorted with tuples
        # first and then lists.  To correctly sort, we need to make
        # sure that all data structures inside the entry list are
        # of the same data type.  The entry list is sorted whenever
        # the entry list is modified, so this is probably the best
        # place to enforce the data type
        self._entries = self._homogenizeEntries(self._entries)

    def _calculateMinAndMaxTime(
        self,
        timestamps: Optional[Iterable[float]] = None,
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Args:
            timestamps: If not provided, defaults to self.timestamps, which is all timestamps
                in self.entries
            minT, maxT: If provided, will be included in the calculation
        """
        timestamps = list(timestamps) if timestamps is not None else self.timestamps
        if minT is not None:
            timestamps.append(minT)
        if maxT is not None:
            timestamps.append(maxT)

        try:
            return (min(timestamps), max(timestamps))
        except ValueError:
            raise errors.TimelessTextgridTierException()

    def appendTier(self: TierType, tier: TierType) -> TierType:
        """Append a tier to the end of this one.

        This tier's maxtimestamp will be lengthened by the amount in the passed in tier.
        """
        if self.tierType != tier.tierType:
            raise errors.ArgumentError(
                f"Cannot append a tier of type {type(tier)} to a tier of type {type(self)}."
            )

        # We're increasing the size of the tier, so of course its intervals
        # may exceed the bounds of the tier's maxTimestamp, triggering
        # errors/warnings--we can ignore those
        appendTier = tier.editTimestamps(
            self.maxTimestamp, constants.ErrorReportingMode.SILENCE
        )

        return self.new(
            entries=self._entries + appendTier._entries,
            maxTimestamp=self.maxTimestamp + tier.maxTimestamp,
        )

    def find(
        self: "TextgridTier[TextgridEntryType]",
        matchLabel: str,
        substrMatchFlag: bool = False,
        usingRE: bool = False,
    ) -> List[int]:
        """Return the index of all intervals that match the given label.

        Args:
            matchLabel: the label to search for
            substrMatchFlag: if True, match any label containing matchLabel.
                if False, label must be the same as matchLabel.
            usingRE: if True, matchLabel is interpreted as a regular expression

        Returns:
            A list of indicies
        """
        returnList: List[int] = []
        if usingRE:
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

    def union(self: TierType, tier: TierType) -> TierType:
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
        self: TierType,
        offset: float,
        reportingMode: Literal["silence", "warning", "error"] = "warning",
    ) -> TierType:  # pragma: no cover
        pass

    @abstractmethod
    def insertEntry(
        self,
        entry: EntryType,
        collisionMode: Literal["replace", "merge", "error"] = "error",
        collisionReportingMode: Literal["silence", "warning"] = "warning",
    ) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def dejitter(
        self: TierType,
        referenceTier: TierType,
        maxDifference: float = 0.001,
    ) -> TierType:  # pragma: no cover
        pass

    @abstractmethod
    def eraseRegion(
        self: TierType,
        start: float,
        end: float,
        collisionMode: Literal["truncate", "categorical", "error"] = "error",
        doShrink: bool = True,
    ) -> TierType:  # pragma: no cover
        pass

    @abstractmethod
    def crop(
        self: TierType,
        cropStart: float,
        cropEnd: float,
        mode: Literal["strict", "lax", "truncated"],
        rebaseToZero: bool,
    ) -> TierType:  # pragma: no cover
        pass

    @abstractmethod
    def insertSpace(
        self: TierType,
        start: float,
        duration: float,
        collisionMode: Literal["stretch", "split", "no_change", "error"],
    ) -> TierType:  # pragma: no cover
        pass

    def deleteEntry(self, entry: EntryType) -> None:
        """Removes an entry from the entries"""
        self._entries.remove(entry)

    @abstractmethod
    def toZeroCrossings(self: TierType, wavFN: str) -> TierType:  # pragma: no cover
        pass

    @abstractmethod
    def validate(self, reportingMode: Literal["silence", "warning", "error"]) -> bool:
        pass  # pragma: no cover
