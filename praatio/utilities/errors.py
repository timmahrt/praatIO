from typing import List

from praatio.utilities import constants


class PraatioException(Exception):
    pass


class SafeZipException(PraatioException):
    pass


class FileNotFound(PraatioException):
    def __init__(self, fullPath: str):
        super(FileNotFound, self).__init__()
        self.fullPath = fullPath

    def __str__(self):
        return "File not found:\n%s" % self.fullPath


class ParsingError(PraatioException):
    pass


class ArgumentError(PraatioException):
    pass


class UnexpectedError(PraatioException):
    pass


class WrongOption(PraatioException):
    def __init__(self, argumentName: str, givenValue: str, availableOptions: List[str]):
        self.argumentName = argumentName
        self.givenValue = givenValue
        self.availableOptions = availableOptions

    def __str__(self):
        return (
            f"For argument '{self.argumentName}' was given the value '{self.givenValue}'. "
            f"However, expected one of [{', '.join(self.availableOptions)}]"
        )


class TextgridException(PraatioException):
    pass


class DuplicateTierName(TextgridException):
    pass


class OutOfBounds(TextgridException):
    pass


class CollisionError(TextgridException):
    pass


class TimelessTextgridTierException(TextgridException):
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


# When the state of a textgrid has to change in a way the user did
# not expect (e.g. a new interval was added that is longer
# than the maxTimestamp, causing maxTimestamp to be lengthened)
class TextgridStateAutoModified(TextgridException):
    pass


class TextgridStateError(TextgridException):
    pass


class TierNameExistsError(TextgridException):
    pass


class IncompatibleTierError(TextgridException):
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


class PraatExecutionFailed(PraatioException):
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


class EndOfAudioData(PraatioException):
    pass


class FindZeroCrossingError(PraatioException):
    def __init__(self, startTime: float, endTime: float):
        super(FindZeroCrossingError, self).__init__()

        self.startTime = startTime
        self.endTime = endTime

    def __str__(self):
        retString = "No zero crossing found between %f and %f"
        return retString % (self.startTime, self.endTime)


class NormalizationException(PraatioException):
    def __str__(self):
        return (
            "Local normalization will nullify the effect of global normalization. "
            "Local normalization should be used to examine local phenomena "
            "(e.g. max pitch in a segment of running speech)."
            "Global normalization should be used to examine global phenomena "
            "(e.g. the pitch range of a speaker)."
        )
