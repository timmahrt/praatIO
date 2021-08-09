"""
KlattGrid and related classes.

KlattGrids can be used for synthesizing and manipulating speech
"""
import io

from typing import List, Optional, Dict, Callable, Union

from praatio.data_classes import textgrid
from praatio.data_classes import textgrid_tier
from praatio.utilities import errors


class _KlattBaseTier(object):
    def __init__(self, name: str):
        self.tierNameList: List[str] = []  # Preserves the order of the tiers
        self.tierDict: Dict[str, "_KlattBaseTier"] = {}
        self.name = name
        self.minTimestamp = None
        self.maxTimestamp = None

    def __eq__(self, other):
        isEqual = True
        isEqual &= self.name == other.name
        isEqual &= self.minTimestamp == other.minTimestamp
        isEqual &= self.maxTimestamp == other.maxTimestamp

        isEqual &= self.tierNameList == other.tierNameList
        if isEqual:
            for tierName in self.tierNameList:
                isEqual &= self.tierDict[tierName] == other.tierDict[tierName]

        return isEqual

    def addTier(self, tier, tierIndex=None) -> None:

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


class KlattContainerTier(_KlattBaseTier):
    """
    Contains a set of intermediate tiers
    """

    def getAsText(self):
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

    def modifySubtiers(self, tierName: str, modFunc) -> None:
        """
        Modify values in every tier contained in the named intermediate tier
        """
        kit = self.tierDict[tierName]
        for name in kit.tierNameList:
            subpointTier = kit.tierDict[name]
            subpointTier.modifyValues(modFunc)


class KlattIntermediateTier(_KlattBaseTier):
    """
    Has many point tiers that are semantically related (e.g. formant tiers)
    """

    def getAsText(self):
        outputTxt = ""
        headerTxt = "%s: size=%d\n" % (self.name, len(self.tierNameList))

        for name in self.tierNameList:
            outputTxt += self.tierDict[name].getAsText()

        outputTxt = headerTxt + outputTxt

        return outputTxt


class KlattPointTier(textgrid_tier.TextgridTier):
    """
    A Klatt tier not contained within another tier
    """

    def __init__(
        self,
        name: str,
        entryList: List,
        minT: Optional[float] = None,
        maxT: Optional[float] = None,
    ):

        entryList = [(float(time), label) for time, label in entryList]

        # Determine the min and max timestamps
        timeList = [time for time, label in entryList]
        if minT is not None:
            timeList.append(float(minT))
        if maxT is not None:
            timeList.append(float(maxT))

        try:
            setMinT = min(timeList)
            setMaxT = max(timeList)
        except ValueError:
            raise errors.TimelessTextgridTierException()

        super(KlattPointTier, self).__init__(name, entryList, setMinT, setMaxT)

    def crop(self):
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

    def validate(self):
        raise NotImplementedError

    def modifyValues(self, modFunc: Callable[[float], bool]) -> None:
        newEntryList = [
            (timestamp, modFunc(float(value))) for timestamp, value in self.entryList
        ]

        self.entryList = newEntryList

    def getAsText(self) -> str:
        outputList = []
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("%s? <exists> " % self.name)
        outputList.append("xmin = %s" % repr(self.minTimestamp))
        outputList.append("xmax = %s" % repr(self.maxTimestamp))

        if self.name not in ["phonation", "vocalTract", "coupling", "frication"]:
            outputList.append("points: size= %d" % len(self.entryList))

        for i, entry in enumerate(self.entryList):
            outputList.append("points [%d]:" % (i + 1))
            outputList.append("    number = %s" % repr(entry[0]))
            outputList.append("    value = %s" % repr(entry[1]))

        return "\n".join(outputList) + "\n"


class KlattSubPointTier(KlattPointTier):
    """
    Tiers contained in a KlattIntermediateTier
    """

    def getAsText(self) -> str:
        outputList = []
        outputList.append("%s:" % self.name)
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("    xmin = %s" % repr(self.minTimestamp))
        outputList.append("    xmax = %s" % repr(self.maxTimestamp))
        outputList.append("    points: size = %d" % len(self.entryList))

        for i, entry in enumerate(self.entryList):
            outputList.append("    points [%d]:" % (i + 1))
            outputList.append("        number = %s" % repr(entry[0]))
            outputList.append("        value = %s" % repr(entry[1]))

        return "\n".join(outputList) + "\n"


class Klattgrid(textgrid.Textgrid):
    def save(self, fn: str, minimumIntervalLength: Optional[float] = None):
        """

        minimumIntervalLength is used for compatibility with Textgrid.save()
            but it has no impact on a Klattgrid
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

        for tierName in self.tierNameList:
            outputTxt += self.tierDict[tierName].getAsText()

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
    newDataList = []
    for row in dataList:
        row = row.rstrip()
        try:
            if "min" in row or "max" in row:
                raise errors.ParsingError(
                    f"Found unexpected keyword 'min' or 'max' in row '{row}'"
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
