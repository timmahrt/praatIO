import os
import contextlib
import unittest

import pytest

from praatio import textgrid
from praatio.utilities.constants import Interval, INTERVAL_TIER, Point


def areTheSameFiles(fn1, fn2, fileHandler, *args):
    """
    Tests that files contain the same data

    If fileHandler is a textgrid file reader like
    textgrid.openTextgrid then we can compare
    a shortTextgrid and a longTextgrid.

    If fileHandler is readFile or io.open, etc then the raw
    text will be compared.
    """
    data1 = fileHandler(fn1, *args)
    data2 = fileHandler(fn2, *args)

    return data1 == data2


def supressStdout(func):
    # https://stackoverflow.com/a/28321717/3787959
    def wrapper(*a, **ka):
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull):
                func(*a, **ka)

    return wrapper


class _DecoratedMethodsClass(type):
    def __new__(cls, name, bases, local):
        for attr in local:
            value = local[attr]
            if callable(value):
                local[attr] = pytest.mark.no_cover(value)  # Ignoring coverage
        return type.__new__(cls, name, bases, local)


class CoverageIgnoredTest(unittest.TestCase, metaclass=_DecoratedMethodsClass):
    pass


def makeIntervalTier(name="words", intervals=None, minT=0, maxT=5.0):
    if intervals is None:
        intervals = [Interval(1, 2, "hello"), Interval(3.5, 4.0, "world")]
    return textgrid.IntervalTier(name, intervals, minT, maxT)


def makePointTier(name="pitch_values", points=None, minT=0, maxT=5.0):
    if points is None:
        points = [Point(1.3, "55"), Point(3.7, "99")]
    return textgrid.PointTier(name, points, minT, maxT)
