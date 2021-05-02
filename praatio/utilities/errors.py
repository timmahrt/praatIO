from typing import List, Union

from praatio.utilities import constants


class TextgridCollisionException(Exception):
    def __init__(
        self,
        tierName: str,
        insertInterval: Union[constants.Point, constants.Interval],
        collisionList: List[constants.Interval],
    ):
        super(TextgridCollisionException, self).__init__()
        self.tierName = tierName
        self.insertInterval = insertInterval
        self.collisionList = collisionList

    def __str__(self):
        return (
            f"Attempted to insert interval {self.insertInterval} into tier {self.tierName} "
            f"of textgrid but overlapping entries {self.collisionList} already exist"
        )


class TimelessTextgridTierException(Exception):
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


class BadIntervalError(Exception):
    def __init__(self, start: float, end: float, label: str):
        super(BadIntervalError, self).__init__()
        self.start = start
        self.end = end
        self.label = label

    def __str__(self):
        return (
            "Problem with interval--could not create textgrid "
            f"({self.start},{self.end},{self.label})"
        )


class BadFormatException(Exception):
    def __init__(self, selectedFormat: str, validFormatOptions: List[str]):
        super(BadFormatException, self).__init__()
        self.selectedFormat = selectedFormat
        self.validFormatOptions = validFormatOptions

    def __str__(self):
        validFormatOptionsStr = ", ".join(self.validFormatOptions)
        return (
            f"Problem with format.  Received {self.selectedFormat} "
            f"but format must be one of {validFormatOptionsStr}"
        )


class IncompatibleTierError(Exception):
    def __init__(self, tier):
        super(IncompatibleTierError, self).__init__()
        self.tier = tier
        if self.tier.tierType == constants.INTERVAL_TIER:
            self.otherTierType = constants.POINT_TIER
        else:
            self.otherTierType = constants.INTERVAL_TIER

    def __str__(self):
        return (
            f"Incompatible tier type.  Tier with name {self.tier.name} has type"
            f"{self.tier.tierType} but expected {self.otherTierType}"
        )


class FileNotFound(Exception):
    def __init__(self, fullPath: str):
        super(FileNotFound, self).__init__()
        self.fullPath = fullPath

    def __str__(self):
        return "File not found:\n%s" % self.fullPath


class PraatExecutionFailed(Exception):
    def __init__(self, cmdList: List[str]):
        super(PraatExecutionFailed, self).__init__()
        self.cmdList = cmdList

    def __str__(self):
        errorStr = (
            "\nPraat Execution Failed.  Please check the following:\n"
            "- Praat exists in the location specified\n"
            "- Praat script can execute ok outside of praat\n"
            "- script arguments are correct\n\n"
            "If you can't locate the problem, I recommend using "
            "absolute paths rather than relative "
            "paths and using paths without spaces in any folder "
            "or file names\n\n"
            "Here is the command that python attempted to run:\n"
        )
        cmdTxt = " ".join(self.cmdList)
        return errorStr + cmdTxt


class EndOfAudioData(Exception):
    pass


class FindZeroCrossingError(Exception):
    def __init__(self, startTime: float, endTime: float):
        super(FindZeroCrossingError, self).__init__()

        self.startTime = startTime
        self.endTime = endTime

    def __str__(self):
        retString = "No zero crossing found between %f and %f"
        return retString % (self.startTime, self.endTime)
