from typing import List

from praatio.utilities import constants


class TextgridCollisionException(Exception):
    def __init__(
        self,
        tierName: str,
        insertInterval: constants.Interval,
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
    def __init__(self, start: float, stop: float, label: str):
        super(BadIntervalError, self).__init__()
        self.start = start
        self.stop = stop
        self.label = label

    def __str__(self):
        return (
            "Problem with interval--could not create textgrid "
            f"({self.start},{self.stop},{self.label})"
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
