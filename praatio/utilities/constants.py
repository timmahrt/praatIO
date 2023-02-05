"""
Constant values and primitive definitions that can be shared throughout the code
"""
from collections import namedtuple
import math

from typing_extensions import Final

INTERVAL_TIER: Final = "IntervalTier"
POINT_TIER: Final = "TextTier"


# https://stackoverflow.com/questions/34570814/equality-overloading-for-namedtuple
class Interval(namedtuple("Interval", ["start", "end", "label"])):
    def __eq__(self, other):
        if not isinstance(other, Interval):
            return False

        return (
            math.isclose(self.start, other.start)
            and math.isclose(self.end, other.end)
            and self.label == other.label
        )

    def __ne__(self, other):
        return not self == other


class Point(namedtuple("Point", ["time", "label"])):
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False

        return (
            math.isclose(self.time, other.time, abs_tol=1e-14)
            and self.label == other.label
        )

    def __ne__(self, other):
        return not self == other


MIN_INTERVAL_LENGTH: Final = 0.00000001  # Arbitrary threshold


class TextgridFormats:
    LONG_TEXTGRID: Final = "long_textgrid"
    SHORT_TEXTGRID: Final = "short_textgrid"
    JSON: Final = "json"
    TEXTGRID_JSON: Final = "textgrid_json"

    validOptions = [LONG_TEXTGRID, SHORT_TEXTGRID, JSON, TEXTGRID_JSON]


class DataPointTypes:
    POINT: Final = "PointProcess"
    PITCH: Final = "PitchTier"
    DURATION: Final = "DurationTier"

    validOptions = [POINT, PITCH, DURATION]


class CropCollision:
    STRICT: Final = "strict"
    LAX: Final = "lax"
    TRUNCATED: Final = "truncated"

    validOptions = [STRICT, LAX, TRUNCATED]


class ErrorReportingMode:
    SILENCE: Final = "silence"
    WARNING: Final = "warning"
    ERROR: Final = "error"

    validOptions = [SILENCE, WARNING, ERROR]


class IntervalCollision:
    REPLACE: Final = "replace"
    MERGE: Final = "merge"
    ERROR: Final = "error"

    validOptions = [REPLACE, MERGE, ERROR]


class WhitespaceCollision:
    STRETCH: Final = "stretch"
    SPLIT: Final = "split"
    NO_CHANGE: Final = "no_change"
    ERROR: Final = "error"

    validOptions = [STRETCH, SPLIT, NO_CHANGE, ERROR]


class EraseCollision:
    TRUNCATE: Final = "truncate"
    CATEGORICAL: Final = "categorical"
    ERROR: Final = "error"

    validOptions = [TRUNCATE, CATEGORICAL, ERROR]


class DuplicateNames:
    ERROR: Final = "error"
    RENAME: Final = "rename"

    validOptions = [ERROR, RENAME]
