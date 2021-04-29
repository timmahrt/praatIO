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


POINT: Final = "PointProcess"
PITCH: Final = "PitchTier"
DURATION: Final = "DurationTier"
