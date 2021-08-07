from typing import List, Union

from praatio.utilities import constants


class SafeZipException(Exception):
    pass


class ParsingError(Exception):
    pass


class WrongOption(Exception):
    def __init__(self, argumentName: str, givenValue: str, availableOptions: List[str]):
        self.argumentName = argumentName
        self.givenValue = givenValue
        self.availableOptions = availableOptions

    def __str__(self):
        return (
            f"For argument '{self.argumentName}' was given the value '{self.givenValue}'. "
            f"However, expected one of [{', '.join(self.availableOptions)}]"
        )


class PraatioException(Exception):
    pass


class TextgridException(Exception):
    pass


class DuplicateTierName(TextgridException):
    pass


class TextgridCollisionException(TextgridException):
    def __init__(
        self,
        tierName: str,
        insertInterval: Union[constants.Point, constants.Interval],
        collisionList: List[constants.Interval],
    ):
        super(TextgridCollisionException, self).__init__()
        self.tierName = tierName
        self.insertInterval = tuple(insertInterval)
        self.collisionList = [tuple(interval) for interval in collisionList]

    def __str__(self):
        return (
            f"Attempted to insert interval {self.insertInterval} into tier {self.tierName} "
            f"of textgrid but overlapping entries {self.collisionList} already exist"
        )


class TimelessTextgridTierException(Exception):
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


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


class NormalizationException(Exception):
    def __str__(self):
        return (
            "Local normalization will nullify the effect of global normalization. "
            "Local normalization should be used to examine local phenomena "
            "(e.g. max pitch in a segment of running speech)."
            "Global normalization should be used to examine global phenomena "
            "(e.g. the pitch range of a speaker)."
        )
