"""
Functions for reading/writing/manipulating klattgrid files

A klattgrid can be used for speech synthesis/resynthesis.
For more information on the praat klattgrid:
http://www.fon.hum.uva.nl/praat/manual/KlattGrid.html

There are three kinds of data types in a klattgrid:
null tiers (contain no data points -- seem to function as headers for a
            set of regular tiers)
regular tiers
embedded tiers

In this code:
null tiers and regular tiers are both represented by KlattPointTier

embedded tiers contain tiers of tiers (3 layers)
A KlattContainerTier contains a list of KlattIntermediateTiers which
contains a list of KlattSubPointTiers.  Only the KlattSubPointTiers contain
any points

see **examples/klatt_resynthesis.py**
"""

import io
from os.path import join
from typing import List, Tuple, Optional

from praatio.data_classes.klattgrid import (
    Klattgrid,
    KlattPointTier,
    KlattContainerTier,
    KlattSubPointTier,
    KlattIntermediateTier,
)
from praatio.utilities import utils


def openKlattgrid(fnFullPath: str) -> Klattgrid:

    try:
        with io.open(fnFullPath, "r", encoding="utf-16") as fd:
            data = fd.read()
    except UnicodeError:
        with io.open(fnFullPath, "r", encoding="utf-8") as fd:
            data = fd.read()
    data = data.replace("\r\n", "\n")

    # Right now, can only open normal klatt grid and not short ones
    kg = _openNormalKlattgrid(data)

    return kg


def wavToKlattgrid(
    praatEXE: str,
    inputFullPath: str,
    outputFullPath: str,
    timeStep: float = 0.005,
    numFormants: int = 5,
    maxFormantFreq: float = 5500.0,
    windowLength: float = 0.025,
    preEmphasis: float = 50.0,
    pitchFloor: float = 60.0,
    pitchCeiling: float = 600.0,
    minPitch: float = 50.0,
    subtractMean: bool = True,
    scriptFN: Optional[str] = None,
) -> None:
    """
    Extracts the klattgrid from a wav file

    The default values are the same as the ones used in praat
    """

    if subtractMean is True:
        subtractMeanStr = "yes"
    else:
        subtractMeanStr = "no"

    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "sound_to_klattgrid.praat")

    utils.runPraatScript(
        praatEXE,
        scriptFN,
        [
            inputFullPath,
            outputFullPath,
            timeStep,
            numFormants,
            maxFormantFreq,
            windowLength,
            preEmphasis,
            pitchFloor,
            pitchCeiling,
            minPitch,
            subtractMeanStr,
        ],
    )


def resynthesize(
    praatEXE: str,
    wavFN: str,
    klattFN: str,
    outputWavFN: str,
    doCascade: bool = True,
    scriptFN: Optional[str] = None,
) -> None:

    if doCascade:
        method = "Cascade"
    else:
        method = "Parallel"

    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "resynthesize_from_klattgrid.praat")

    #  Praat crashes on exit after resynthesis with a klattgrid
    utils.runPraatScript(praatEXE, scriptFN, [wavFN, klattFN, outputWavFN, method])


def _openNormalKlattgrid(data: str) -> Klattgrid:

    kg = Klattgrid()

    # Toss header
    data = data.split("\n\n", 1)[1]

    # Not sure if this is needed
    startI = data.index("points")
    startI = data.index("\n", startI)

    # Find sections
    sectionIndexList = _findIndicies(data, "<exists>")

    sectionIndexList.append(-1)

    for i in range(len(sectionIndexList) - 1):
        dataTuple = _getSectionHeader(data, sectionIndexList, i)
        name, minT, maxT, sectionData, sectionTuple = dataTuple

        # Container Tier
        if name in [
            "oral_formants",
            "nasal_formants",
            "nasal_antiformants",
            "tracheal_formants",
            "tracheal_antiformants",
            "delta_formants",
            "frication_formants",
        ]:

            kct = _proccessContainerTierInput(sectionData, name)
            kg.addTier(kct)

        else:

            # Process entries if this tier has any
            entryList = _buildEntryList(sectionTuple)
            tier = KlattPointTier(name, entryList, minT, maxT)
            kg.addTier(tier)

    return kg


def _proccessContainerTierInput(sectionData: str, name: str):
    sectionData = sectionData.split("\n", 3)[-1]

    formantIndexList = _findIndicies(sectionData, "formants")

    subFilterList = [
        "bandwidths",
        "oral_formants_amplitudes",
        "nasal_formants_amplitudes",
        "tracheal_formants_amplitudes",
        "frication_formants_amplitudes",
    ]

    # Find the index of all the different data sections
    subFilterIndexList = [
        _findIndicies(sectionData, subName) for subName in subFilterList
    ]

    # 'Formant' search query finds duplicates -- remove them
    newFormantList = []
    for value in formantIndexList:
        if all([value not in subList for subList in subFilterIndexList]):
            newFormantList.append(value)
    formantIndexList = newFormantList

    # Combine regular query with formant query
    indexListOfLists = [
        formantIndexList,
    ] + subFilterIndexList

    # Flatten index list
    masterIndexList = [value for sublist in indexListOfLists for value in sublist]
    masterIndexList.sort()

    # If an index list is last, it it needs to include '-1' to capture the
    # rest of the data
    for subList in indexListOfLists:
        try:
            val = subList[-1]
        except IndexError:
            continue
        ii = masterIndexList.index(val)  # Index of the index
        try:
            subList.append(masterIndexList[ii + 1] - 1)
        except IndexError:
            subList.append(-1)

    # Build the tier structure
    kct = KlattContainerTier(name)
    for indexList in indexListOfLists:
        if indexList == []:
            continue
        tierList = []
        for j in range(len(indexList) - 1):
            try:
                tmpTuple = _getSectionHeader(sectionData, indexList, j)
            except ValueError:
                continue
            subName, subMin, subMax, _, subTuple = tmpTuple
            subName = subName[:-1]

            entryList = _buildEntryList(subTuple)
            tier = KlattSubPointTier(subName, entryList, subMin, subMax)
            tierList.append(tier)
        kit = KlattIntermediateTier(subName.split()[0])
        for tier in tierList:
            kit.addTier(tier)
        kct.addTier(kit)

    return kct


def _findIndicies(data, keyword):
    indexList = utils.findAll(data, keyword)
    indexList = [data.rfind("\n", 0, i) for i in indexList]

    return indexList


def _getSectionHeader(data, indexList, i):
    sectionStart = indexList[i]
    sectionEnd = indexList[i + 1]
    sectionData = data[sectionStart:sectionEnd].strip()
    sectionTuple = sectionData.split("\n", 4)

    subheader, minr, maxr = sectionTuple[:3]
    name = subheader.split("?")[0].strip()
    minT = float(minr.split("=")[1].strip())
    maxT = float(maxr.split("=")[1].strip())

    tail = sectionTuple[3:]

    return name, minT, maxT, sectionData, tail


def _buildEntryList(sectionTuple):
    entryList = []
    if len(sectionTuple) > 1:  # Has points
        npoints = float(sectionTuple[0].split("=")[1].strip())
        if npoints > 0:
            entryList = _processSectionData(sectionTuple[1])

    return entryList


def _processSectionData(sectionData: str) -> List[Tuple[float, float]]:

    sectionData += "\n"

    startI = 0
    tupleList = []
    while True:
        try:
            startI = sectionData.index("=", startI) + 1  # Past the equal sign
        except ValueError:  # No more data
            break

        endI = sectionData.index("\n", startI)
        time = float(sectionData[startI:endI].strip())

        startI = sectionData.index("=", endI) + 1  # Just past the '=' sign
        endI = sectionData.index("\n", startI)
        value = float(sectionData[startI:endI].strip())

        startI = endI
        tupleList.append((time, value))

    return tupleList
