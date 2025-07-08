"""Constant values and primitive definitions that can be shared throughout the code."""
from typing import NamedTuple, Any
import math

from typing_extensions import Final

from praatio.utilities import errors

INTERVAL_TIER: Final = "IntervalTier"
POINT_TIER: Final = "TextTier"


# https://stackoverflow.com/questions/34570814/equality-overloading-for-namedtuple
class Interval(NamedTuple):
    start: float
    end: float
    label: str

    @classmethod
    def build(cls, *args: Any):
        """
        Safe constructor for Interval.

        Interval(start, end, label) doesn't check the type at runtime.
        Should only be used on validated data.

        Interval.build() is robust and performs type conversion and label stripping.
        It accepts either 3 arguments (start, end, label),
        or 1 argument (another Interval or a tuple or list of 3 elements).

        Raises:
            ArgumentError: Either wrong number of arguments, or failed to convert
                the arguments to float or string.
        """
        try:
            start, end, label = args[0] if len(args) == 1 else args
            return cls(float(start), float(end), str(label).strip())
        except (TypeError, ValueError):
            raise errors.ArgumentError(f"Cannot build Interval from {args}")

    def __eq__(self, other: Any):
        return (
            isinstance(other, Interval)
            and math.isclose(self.start, other.start)
            and math.isclose(self.end, other.end)
            and self.label == other.label
        )

    def __ne__(self, other: Any):
        return not self == other

    def __add__(self, offset: float):
        """Time shift forward by offset."""
        return Interval(self.start + offset, self.end + offset, self.label)

    def __sub__(self, offset: float):
        """Time shift backward by offset."""
        return Interval(self.start - offset, self.end - offset, self.label)

    def __repr__(self):
        return str(tuple(self))


class Point(NamedTuple):
    time: float
    label: str

    @classmethod
    def build(cls, *args: Any):
        """
        Safe constructor for Point.

        Point(time, label) doesn't check the type at runtime.
        Should only be used on validated data.

        Point.build() is robust and performs type conversion and label stripping.
        It accepts either 2 arguments (time, label),
        or 1 argument (another Point or a tuple or list of 2 elements).

        Raises:
            ArgumentError: Either wrong number of arguments, or failed to convert
                the arguments to float or string.
        """
        try:
            time, label = args[0] if len(args) == 1 else args
            return cls(float(time), str(label).strip())
        except (TypeError, ValueError):
            raise errors.ArgumentError(f"Cannot build Point from {args}")

    def __eq__(self, other: Any):
        return (
            isinstance(other, Point)
            and math.isclose(self.time, other.time, abs_tol=1e-14)
            and self.label == other.label
        )

    def __ne__(self, other: Any):
        return not self == other

    def __add__(self, offset: float):
        """Time shift forward by offset."""
        return Point(self.time + offset, self.label)

    def __sub__(self, offset: float):
        """Time shift backward by offset."""
        return Point(self.time - offset, self.label)

    def __repr__(self):
        return str(tuple(self))


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


class NameStyle:
    NAME_AND_I_AND_LABEL = "name_and_i_and_label"
    NAME_AND_LABEL = "name_and_label"
    NAME_AND_I = "name_and_i"
    LABEL = "label"

    validOptions = [NAME_AND_I_AND_LABEL, NAME_AND_LABEL, NAME_AND_I, LABEL]
