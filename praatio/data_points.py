"""
Code for reading, writing, and representing less complicated praat data files

see **examples/get_vowel_points.py**
"""

import io
from typing import Tuple

from praatio.data_classes.data_point import PointObject1D, PointObject2D


def open1DPointObject(fn: str) -> PointObject1D:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index("=", start)
            except ValueError:
                break

            pointVal, start = _getNextValue(data, start)
            dataList.append((float(pointVal),))

        po = PointObject1D(dataList, objectType, minT, maxT)

    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataList = [(float(val),) for val in data.split("\n") if val.strip() != ""]
        po = PointObject1D(dataList, objectType, minT, maxT)

    return po


def open2DPointObject(fn: str) -> PointObject2D:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index("=", start)
            except ValueError:
                break

            timeVal, start = _getNextValue(data, start)

            try:
                start = data.index("=", start)
            except ValueError:
                break

            pointVal, start = _getNextValue(data, start)
            dataList.append(
                (
                    float(timeVal),
                    float(pointVal),
                )
            )

        po = PointObject2D(dataList, objectType, minT, maxT)

    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataStrList = data.split("\n")
        dataList = [
            (float(dataStrList[i]), float(dataStrList[i + 1]))
            for i in range(0, len(dataStrList), 2)
            if dataStrList[i].strip() != ""
        ]
        po = PointObject2D(dataList, objectType, minT, maxT)

    return po


def _parseNormalHeader(fn: str) -> Tuple[str, str, float, float]:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()

    chunkedData = data.split("\n", 7)

    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()

    data = chunkedData[-1]
    maxT = float(chunkedData[-4].split("=")[-1].strip())
    minT = float(chunkedData[-5].split("=")[-1].strip())

    return data, objectType, minT, maxT


def _getNextValue(data: str, start: int) -> Tuple[str, int]:
    end = data.index("\n", start)
    value = data[start + 1 : end]
    return value, end


def _parseShortHeader(fn: str) -> Tuple[str, str, float, float]:
    with io.open(fn, "r", encoding="utf-8") as fd:
        data = fd.read()

    chunkedData = data.split("\n", 6)

    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()

    data = chunkedData[-1]
    maxT = float(chunkedData[-3])
    minT = float(chunkedData[-4])

    return data, objectType, minT, maxT
