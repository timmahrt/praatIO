"""
Functions for reading/writing/manipulating textgrid files.

This file links the main data structures for representing Textgrid data:
Textgrid, IntervalTier, and PointTier

A Textgrid is a container for multiple annotation tiers.  Tiers can contain
either interval data (IntervalTier) or point data (PointTier).
Tiers in a Textgrid are ordered and must contain a unique name.

openTextgrid() can be used to open a textgrid file.
Textgrid.save() can be used to save a Textgrid object to a file.

Historically, these three classes lived in this file. To
make maintance easier, they were split off.  You can still access
them from this file as before, but please check out the respective
files for more documentation on each class:
IntervalTier in data_classes/interval_tier.py
PointTier in data_classes/point_tier.py
Textgrid in data_classes/textgrid.py

see the **examples/** directory for examples using textgrid.py
"""

import io
from typing import (
    Union,
    Type,
)

from typing_extensions import Literal


from praatio.utilities.constants import (
    INTERVAL_TIER,
)
from praatio.data_classes.interval_tier import IntervalTier
from praatio.data_classes.point_tier import PointTier
from praatio.data_classes.textgrid import Textgrid
from praatio.utilities import textgrid_io
from praatio.utilities import utils
from praatio.utilities import constants
from praatio.utilities import errors


def openTextgrid(
    fnFullPath: str,
    includeEmptyIntervals: bool,
    reportingMode: Literal["silence", "warning", "error"] = "warning",
    duplicateNamesMode: Literal["error", "rename"] = "error",
) -> Textgrid:
    """
    Opens a textgrid file (.TextGrid and .json are both fine)

    Args:
        fnFullPath (str): the path to the textgrid to open
        includeEmptyIntervals (bool): if False, points and intervals with
             an empty label '' are not included in the returned Textgrid

    Returns:
        Textgrid

    https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html
    """
    utils.validateOption("reportingMode", reportingMode, constants.ErrorReportingMode)
    utils.validateOption(
        "duplicateNamesMode", duplicateNamesMode, constants.DuplicateNames
    )
    try:
        with io.open(fnFullPath, "r", encoding="utf-16") as fd:
            data = fd.read()
    except UnicodeError:
        with io.open(fnFullPath, "r", encoding="utf-8") as fd:
            data = fd.read()

    tgAsDict = textgrid_io.parseTextgridStr(data, includeEmptyIntervals)

    tierNames = []
    for tier in tgAsDict["tiers"]:
        name = tier["name"]
        if name in tierNames:
            if duplicateNamesMode == constants.DuplicateNames.ERROR:
                raise errors.DuplicateTierName(
                    f"Your textgrid contains tiers with the same name '{name}'. "
                    "This is not allowed. It is recommended that you rename them. "
                    "If you set openTextgrid(..., duplicateNamesMode='rename'), praatio "
                    "will automatically append numbers to the end of tiers to ensure they "
                    "are unique."
                )
            elif duplicateNamesMode == constants.DuplicateNames.RENAME:
                newName = name
                i = 2
                while newName in tierNames:
                    newName = f"{name}_{i}"
                    i += 1
                name = newName
                tier["name"] = name
        tierNames.append(name)

    return _dictionaryToTg(tgAsDict, reportingMode)


def _dictionaryToTg(
    tgAsDict: dict, reportingMode: Literal["silence", "warning", "error"]
) -> Textgrid:
    """Converts a dictionary representation of a textgrid to a Textgrid"""
    utils.validateOption("reportingMode", reportingMode, constants.ErrorReportingMode)

    tg = Textgrid()
    tg.minTimestamp = tgAsDict["xmin"]
    tg.maxTimestamp = tgAsDict["xmax"]

    for tierAsDict in tgAsDict["tiers"]:
        klass: Union[Type[PointTier], Type[IntervalTier]]
        if tierAsDict["class"] == INTERVAL_TIER:
            klass = IntervalTier
        else:
            klass = PointTier
        tier = klass(
            tierAsDict["name"],
            tierAsDict["entries"],
            tierAsDict["xmin"],
            tierAsDict["xmax"],
        )
        tg.addTier(tier, reportingMode=reportingMode)

    return tg
