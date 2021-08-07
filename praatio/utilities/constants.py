"""
Constant values and primitive definitions that can be shared throughout the code
"""
from collections import namedtuple

from typing_extensions import Final

INTERVAL_TIER: Final = "IntervalTier"
POINT_TIER: Final = "TextTier"

Interval: Final = namedtuple("Interval", ["start", "end", "label"])  # interval entry
Point: Final = namedtuple("Point", ["time", "label"])  # point entry

MIN_INTERVAL_LENGTH: Final = 0.00000001  # Arbitrary threshold


class TextgridFormats:
    LONG_TEXTGRID: Final = "long_textgrid"
    SHORT_TEXTGRID: Final = "short_textgrid"
    JSON: Final = "json"

    validOptions = [LONG_TEXTGRID, SHORT_TEXTGRID, JSON]


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
