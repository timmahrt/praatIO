"""KlattGrid and related classes.

KlattGrids can be used for synthesizing and manipulating speech
"""
import io
from typing import List, Optional, Dict, Callable, Union, Any, TypeVar, Generic

from praatio.utilities.constants import KlattPoint
from praatio.data_classes.textgrid import BaseTextgrid
from praatio.data_classes.textgrid_tier import TextgridTier
from praatio.utilities import errors


class KlattPointTier(TextgridTier[KlattPoint]):
    """A Klatt tier not contained within another tier."""
    entryType = KlattPoint

    @property
    def timestamps(self) -> List[float]:
        return sorted(set(time for time, _ in self._entries))

    def crop(self):
        raise NotImplementedError

    def dejitter(self):
        raise NotImplementedError

    def deleteEntry(self, entry):
        raise NotImplementedError

    def editTimestamps(self):
        raise NotImplementedError

    def eraseRegion(self):
        raise NotImplementedError

    def insertEntry(self):
        raise NotImplementedError

    def insertSpace(self):
        raise NotImplementedError

    def toZeroCrossings(self):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError

    def modifyValues(self, modFunc: Callable[[float], float]) -> None:
        self._entries = [
            KlattPoint(time, modFunc(value)) for time, value in self.entries
        ]

    def getAsText(self) -> str:
        outputList: List[str] = []
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("%s? <exists> " % self.name)
        outputList.append("xmin = %s" % repr(self.minTimestamp))
        outputList.append("xmax = %s" % repr(self.maxTimestamp))

        if self.name not in ["phonation", "vocalTract", "coupling", "frication"]:
            outputList.append("points: size= %d" % len(self.entries))

        for i, entry in enumerate(self.entries):
            outputList.append("points [%d]:" % (i + 1))
            outputList.append("    number = %s" % repr(entry.time))
            outputList.append("    value = %s" % repr(entry.value))

        return "\n".join(outputList) + "\n"


class KlattSubPointTier(KlattPointTier):
    """Tiers contained in a KlattIntermediateTier."""

    def getAsText(self) -> str:
        outputList: List[str] = []
        outputList.append("%s:" % self.name)
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("    xmin = %s" % repr(self.minTimestamp))
        outputList.append("    xmax = %s" % repr(self.maxTimestamp))
        outputList.append("    points: size = %d" % len(self.entries))

        for i, entry in enumerate(self.entries):
            outputList.append("    points [%d]:" % (i + 1))
            outputList.append("        number = %s" % repr(entry.time))
            outputList.append("        value = %s" % repr(entry.value))

        return "\n".join(outputList) + "\n"


ContainedType = TypeVar("ContainedType", bound=Union[KlattSubPointTier, "_KlattBaseTier"])


class _KlattBaseTier(Generic[ContainedType]):
    def __init__(self, name: str):
        self.tierNameList: List[str] = []  # Preserves the order of the tiers
        self.tierDict: Dict[str, ContainedType] = {}
        self.name = name
        self.minTimestamp = None
        self.maxTimestamp = None

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and self.name == other.name
            and self.minTimestamp == other.minTimestamp
            and self.maxTimestamp == other.maxTimestamp
            and self.tierNameList == other.tierNameList
            and self.tierDict == other.tierDict
        )

    def addTier(self, tier: ContainedType, tierIndex: Optional[int] = None) -> None:
        if tierIndex is None:
            self.tierNameList.append(tier.name)
        else:
            self.tierNameList.insert(tierIndex, tier.name)

        if tier.name in list(self.tierDict.keys()):
            raise errors.TierNameExistsError(
                f"Cannot add tier with name {tier.name} as it already exists in the Klattgrid"
            )
        self.tierDict[tier.name] = tier

        minV = tier.minTimestamp
        if self.minTimestamp is None or (minV is not None and minV < self.minTimestamp):
            self.minTimestamp = minV

        maxV = tier.maxTimestamp
        if self.maxTimestamp is None or (maxV is not None and maxV > self.maxTimestamp):
            self.maxTimestamp = maxV


class KlattIntermediateTier(_KlattBaseTier[KlattSubPointTier]):
    """Has many point tiers that are semantically related (e.g. formant tiers)."""

    def getAsText(self) -> str:
        outputTxt = ""
        headerTxt = "%s: size=%d\n" % (self.name, len(self.tierNameList))

        for name in self.tierNameList:
            outputTxt += self.tierDict[name].getAsText()

        outputTxt = headerTxt + outputTxt

        return outputTxt


class KlattContainerTier(_KlattBaseTier[KlattIntermediateTier]):
    """Contains a set of intermediate tiers."""

    def getAsText(self) -> str:
        outputTxt = ""
        outputTxt += "%s? <exists>\n" % self.name

        try:
            self.minTimestamp = toIntOrFloat(self.minTimestamp)
            outputTxt += "xmin = %s\nxmax = %s\n" % (
                repr(self.minTimestamp),
                repr(self.maxTimestamp),
            )
        except TypeError:
            pass

        for name in self.tierNameList:
            outputTxt += self.tierDict[name].getAsText()

        return outputTxt

    def modifySubtiers(self, tierName: str, modFunc: Callable[[float], bool]) -> None:
        """Modify values in every tier contained in the named intermediate tier."""
        kit = self.tierDict[tierName]
        for name in kit.tierNameList:
            subpointTier = kit.tierDict[name]
            subpointTier.modifyValues(modFunc)


class Klattgrid(BaseTextgrid[Union[KlattPointTier, KlattContainerTier]]):
    def save(self, fn: str, minimumIntervalLength: Optional[float] = None) -> None:
        """
        minimumIntervalLength is used for compatibility with Textgrid.save()
            but it has no impact on a Klattgrid.
        """

        # Header
        outputTxt = ""
        outputTxt += 'File type = "ooTextFile"\n'
        outputTxt += 'Object class = "KlattGrid"\n\n'
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputTxt += "xmin = %s\nxmax = %s\n" % (
            repr(self.minTimestamp),
            repr(self.maxTimestamp),
        )

        for tierName in self.tierNames:
            outputTxt += self._tierDict[tierName].getAsText()

        outputTxt = _cleanNumericValues(outputTxt)

        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(outputTxt)


def toIntOrFloat(val: Union[str, float]) -> float:
    if float(val) - float(int(val)) == 0.0:
        val = int(val)
    else:
        val = float(val)
    return val


def _cleanNumericValues(dataStr: str) -> str:
    dataList = dataStr.split("\n")
    newDataList: List[str] = []
    for row in dataList:
        row = row.rstrip()
        try:
            if "min" in row or "max" in row:
                raise errors.ParsingError(
                    f"Found unexpected keyword 'min' or 'max' in row {row!r}."
                )

            head, tail = row.split("=")
            head = head.rstrip()
            tail = tail.strip()
            try:
                row = str(int(tail))
            except ValueError:
                tail = "%s" % tail
                if float(tail) == 0:
                    tail = "0"
            row = "%s = %s" % (head, tail)
        except (ValueError, errors.ParsingError):  # TODO: Is it really ok?
            pass
        finally:
            newDataList.append(row.rstrip())

    outputTxt = "\n".join(newDataList)

    return outputTxt
