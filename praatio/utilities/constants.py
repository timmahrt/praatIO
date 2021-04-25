"""
Constant values and primitive definitions that can be shared throughout the code
"""
from collections import namedtuple

INTERVAL_TIER = "IntervalTier"
POINT_TIER = "TextTier"

Interval = namedtuple("Interval", ["start", "end", "label"])  # interval entry
Point = namedtuple("Point", ["time", "label"])  # point entry

MIN_INTERVAL_LENGTH = 0.00000001  # Arbitrary threshold

LONG_TEXTGRID = "long_textgrid"
SHORT_TEXTGRID = "short_textgrid"
JSON = "json"

POINT = "PointProcess"
PITCH = "PitchTier"
DURATION = "DurationTier"
