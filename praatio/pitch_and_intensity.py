# coding: utf-8
"""
Functions for working with pitch data

This file depends on the praat script get_pitch_and_intensity.praat
(which depends on praat) to extract pitch and intensity values from
audio data.  Once the data is extracted, there are functions for
data normalization and calculating various measures from the time
stamped output of the praat script (ie **generatePIMeasures()**)

For brevity, 'pitch_and_intensity' is referred to as 'PI'

see **examples/get_pitch_and_formants.py**
"""

import os
from os.path import join
import io
import math
from typing import List, Tuple, Optional, cast

from praatio import data_points
from praatio import praatio_scripts
from praatio import textgrid
from praatio.utilities import errors
from praatio.utilities import my_math
from praatio.utilities import utils
from praatio.utilities.constants import Point


HERTZ = "Hertz"
UNSPECIFIED = "unspecified"
_PITCH_ERROR_TIER_NAME = "pitch errors"


def _extractPIPiecewise(
    inputFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    maxPitch: float,
    tgFN: str,
    tierName: str,
    tmpOutputPath: str,
    sampleStep: float = 0.01,
    silenceThreshold: float = 0.03,
    pitchUnit: str = HERTZ,
    forceRegenerate: bool = True,
    undefinedValue: float = None,
    medianFilterWindowSize: int = 0,
    pitchQuadInterp: bool = False,
) -> List[Tuple[float, ...]]:
    """
    Extracts pitch and int from each labeled interval in a textgrid

    This has the benefit of being faster than using _extractPIFile if only
    labeled regions need to have their pitch values sampled, particularly
    for longer files.

    Returns the result as a list.  Will load the serialized result
    if this has already been called on the appropriate files before
    """
    outputPath = os.path.split(outputFN)[0]
    utils.makeDir(outputPath)

    windowSize = medianFilterWindowSize

    if not os.path.exists(inputFN):
        raise errors.ArgumentError(f"Required folder does not exist: f{inputFN}")

    firstTime = not os.path.exists(outputFN)
    if firstTime or forceRegenerate is True:

        utils.makeDir(tmpOutputPath)
        splitAudioList = praatio_scripts.splitAudioOnTier(
            inputFN, tgFN, tierName, tmpOutputPath, False
        )
        allPIList: List[Tuple[str, str, str]] = []
        for start, _, fn in splitAudioList:
            tmpTrackName = os.path.splitext(fn)[0] + ".txt"
            piList = _extractPIFile(
                join(tmpOutputPath, fn),
                join(tmpOutputPath, tmpTrackName),
                praatEXE,
                minPitch,
                maxPitch,
                sampleStep,
                silenceThreshold,
                pitchUnit,
                forceRegenerate=True,
                medianFilterWindowSize=windowSize,
                pitchQuadInterp=pitchQuadInterp,
            )
            convertedPiList = [
                ("%0.3f" % (float(time) + start), str(pV), str(iV))
                for time, pV, iV in piList
            ]
            allPIList.extend(convertedPiList)

        outputData = [",".join(row) for row in allPIList]
        with open(outputFN, "w") as fd:
            fd.write("\n".join(outputData) + "\n")

    return loadTimeSeriesData(outputFN, undefinedValue=undefinedValue)


def _extractPIFile(
    inputFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    maxPitch: float,
    sampleStep: float = 0.01,
    silenceThreshold: float = 0.03,
    pitchUnit: str = HERTZ,
    forceRegenerate: bool = True,
    undefinedValue: float = None,
    medianFilterWindowSize: int = 0,
    pitchQuadInterp: bool = False,
) -> List[Tuple[float, ...]]:
    """
    Extracts pitch and intensity values from an audio file

    Returns the result as a list.  Will load the serialized result
    if this has already been called on the appropriate files before
    """
    outputPath = os.path.split(outputFN)[0]
    utils.makeDir(outputPath)

    if not os.path.exists(inputFN):
        raise errors.ArgumentError(f"Required folder does not exist: f{inputFN}")

    firstTime = not os.path.exists(outputFN)
    if firstTime or forceRegenerate is True:

        # The praat script uses append mode, so we need to clear any prior
        # result
        if os.path.exists(outputFN):
            os.remove(outputFN)

        if pitchQuadInterp is True:
            doInterpolation = 1
        else:
            doInterpolation = 0

        argList = [
            inputFN,
            outputFN,
            sampleStep,
            minPitch,
            maxPitch,
            silenceThreshold,
            pitchUnit,
            -1,
            -1,
            medianFilterWindowSize,
            doInterpolation,
        ]

        scriptName = "get_pitch_and_intensity.praat"
        scriptFN = join(utils.scriptsPath, scriptName)
        utils.runPraatScript(praatEXE, scriptFN, argList)

    return loadTimeSeriesData(outputFN, undefinedValue=undefinedValue)


def extractIntensity(
    inputFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    sampleStep: float = 0.01,
    forceRegenerate: bool = True,
    undefinedValue: float = None,
) -> List[Tuple[float, ...]]:
    """
    Extract the intensity for an audio file

    Calculates intensity using the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Intensity___.html
    """
    outputPath = os.path.split(outputFN)[0]
    utils.makeDir(outputPath)

    if not os.path.exists(inputFN):
        raise errors.ArgumentError(f"Required folder does not exist: f{inputFN}")

    firstTime = not os.path.exists(outputFN)
    if firstTime or forceRegenerate is True:

        # The praat script uses append mode, so we need to clear any prior
        # result
        if os.path.exists(outputFN):
            os.remove(outputFN)

        argList = [inputFN, outputFN, sampleStep, minPitch, -1, -1]

        scriptName = "get_intensity.praat"
        scriptFN = join(utils.scriptsPath, scriptName)
        utils.runPraatScript(praatEXE, scriptFN, argList)

    return loadTimeSeriesData(outputFN, undefinedValue=undefinedValue)


def extractPitchTier(
    wavFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    maxPitch: float,
    sampleStep: float = 0.01,
    silenceThreshold: float = 0.03,
    forceRegenerate: bool = True,
    medianFilterWindowSize: int = 0,
    pitchQuadInterp: bool = False,
) -> data_points.PointObject2D:
    """
    Extract pitch at regular intervals from the input wav file

    Data is output to a text file and then returned in a list in the form
    [(timeV1, pitchV1), (timeV2, pitchV2), ...]

    sampleStep - the frequency to sample pitch at
    silenceThreshold - segments with lower intensity won't be analyzed
                       for pitch
    forceRegenerate - if running this function for the same file, if False
                      just read in the existing pitch file
    pitchQuadInterp - if True, quadratically interpolate pitch

    Calculates pitch using the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Pitch___.html
    """
    outputPath = os.path.split(outputFN)[0]

    utils.makeDir(outputPath)

    if pitchQuadInterp is True:
        doInterpolation = 1
    else:
        doInterpolation = 0

    if not os.path.exists(wavFN):
        raise errors.ArgumentError(f"Required file does not exist: f{wavFN}")

    firstTime = not os.path.exists(outputFN)
    if firstTime or forceRegenerate is True:
        if os.path.exists(outputFN):
            os.remove(outputFN)

        argList = [
            wavFN,
            outputFN,
            sampleStep,
            minPitch,
            maxPitch,
            silenceThreshold,
            medianFilterWindowSize,
            doInterpolation,
        ]

        scriptName = "get_pitchtier.praat"
        scriptFN = join(utils.scriptsPath, scriptName)
        utils.runPraatScript(praatEXE, scriptFN, argList)

    return data_points.open2DPointObject(outputFN)


def extractPitch(
    wavFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    maxPitch: float,
    sampleStep: float = 0.01,
    silenceThreshold: float = 0.03,
    forceRegenerate: bool = True,
    undefinedValue: float = None,
    medianFilterWindowSize: int = 0,
    pitchQuadInterp: bool = False,
) -> List[Tuple[float, ...]]:
    """
    Extract pitch at regular intervals from the input wav file

    Data is output to a text file and then returned in a list in the form
    [(timeV1, pitchV1), (timeV2, pitchV2), ...]

    sampleStep - the frequency to sample pitch at
    silenceThreshold - segments with lower intensity won't be analyzed
                       for pitch
    forceRegenerate - if running this function for the same file, if False
                      just read in the existing pitch file
    undefinedValue - if None remove from the dataset, otherset set to
                     undefinedValue
    pitchQuadInterp - if True, quadratically interpolate pitch

    Calculates pitch using the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Pitch___.html
    """
    outputPath = os.path.split(outputFN)[0]

    utils.makeDir(outputPath)

    if pitchQuadInterp is True:
        doInterpolation = 1
    else:
        doInterpolation = 0

    if not os.path.exists(wavFN):
        raise errors.ArgumentError(f"Required file does not exist: f{wavFN}")

    firstTime = not os.path.exists(outputFN)
    if firstTime or forceRegenerate is True:
        if os.path.exists(outputFN):
            os.remove(outputFN)

        argList = [
            wavFN,
            outputFN,
            sampleStep,
            minPitch,
            maxPitch,
            silenceThreshold,
            -1,
            -1,
            medianFilterWindowSize,
            doInterpolation,
        ]

        scriptName = "get_pitch.praat"
        scriptFN = join(utils.scriptsPath, scriptName)
        utils.runPraatScript(praatEXE, scriptFN, argList)

    return loadTimeSeriesData(outputFN, undefinedValue=undefinedValue)


def extractPI(
    inputFN: str,
    outputFN: str,
    praatEXE: str,
    minPitch: float,
    maxPitch: float,
    sampleStep: float = 0.01,
    silenceThreshold: float = 0.03,
    pitchUnit: str = HERTZ,
    forceRegenerate: bool = True,
    tgFN: str = None,
    tierName: str = None,
    tmpOutputPath: str = None,
    undefinedValue: float = None,
    medianFilterWindowSize: int = 0,
    pitchQuadInterp: bool = False,
) -> List[Tuple[float, ...]]:
    """
    Extracts pitch and intensity from a file wholesale or piecewise

    If the parameters for a tg are passed in, this will only extract labeled
    segments in a tier of the tg.  Otherwise, pitch will be extracted from
    the entire file.

    male: minPitch=50; maxPitch=350
    female: minPitch=75; maxPitch=450
    pitchUnit: "Hertz", "semitones re 100 Hz", etc

    Calculates pitch and intensity using the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Pitch___.html
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Intensity___.html
    """

    outputPath = os.path.split(outputFN)[0]

    windowSize = medianFilterWindowSize

    if tgFN is None or tierName is None:
        piList = _extractPIFile(
            inputFN,
            outputFN,
            praatEXE,
            minPitch,
            maxPitch,
            sampleStep,
            silenceThreshold,
            pitchUnit,
            forceRegenerate,
            undefinedValue=undefinedValue,
            medianFilterWindowSize=windowSize,
            pitchQuadInterp=pitchQuadInterp,
        )
    else:
        if tmpOutputPath is None:
            tmpOutputPath = join(outputPath, "piecewise_output")
        piList = _extractPIPiecewise(
            inputFN,
            outputFN,
            praatEXE,
            minPitch,
            maxPitch,
            tgFN,
            tierName,
            tmpOutputPath,
            sampleStep,
            silenceThreshold,
            pitchUnit,
            forceRegenerate,
            undefinedValue=undefinedValue,
            medianFilterWindowSize=windowSize,
            pitchQuadInterp=pitchQuadInterp,
        )

    return piList


def loadTimeSeriesData(
    fn: str, undefinedValue: float = None
) -> List[Tuple[float, ...]]:
    """
    For reading the output of get_pitch_and_intensity or get_intensity

    Data should be of the form
    [(time1, value1a, value1b, ...),
     (time2, value2a, value2b, ...), ]
    """
    name = os.path.splitext(os.path.split(fn)[1])[0]

    try:
        with io.open(fn, "r", encoding="utf-8") as fd:
            data = fd.read()
    except IOError:
        print(f"No pitch track for: {name}")
        raise

    dataList = [row.split(",") for row in data.splitlines() if row != ""]

    # The new praat script includes a header
    if dataList[0][0] == "time":
        dataList = dataList[1:]

    newDataList = []
    for row in dataList:
        time = float(row.pop(0))
        entry = [
            time,
        ]
        doSkip = False
        for value in row:
            if "--" in value:
                if undefinedValue is not None:
                    appendValue = undefinedValue
                else:
                    doSkip = True
                    break
            else:
                appendValue = float(value)

            entry.append(appendValue)

        if doSkip is True:
            continue

        newDataList.append(tuple(entry))

    return newDataList


def generatePIMeasures(
    dataList: List[Tuple[float, float, float]],
    tgFN: str,
    tierName: str,
    doPitch: bool,
    medianFilterWindowSize: int = None,
    globalZNormalization: bool = False,
    localZNormalizationWindowSize: int = 0,
) -> List[Tuple[float, ...]]:
    """
    Generates processed values for the labeled intervals in a textgrid

    nullLabelList - labels to ignore in the textgrid.  Defaults to ["",]

    if 'doPitch'=true get pitch measures; if =false get rms intensity
    medianFilterWindowSize: if none, no filtering is done
    globalZNormalization: if True, values are normalized with the mean
                          and stdDev of the data in dataList
    localZNormalization: if greater than 1, values are normalized with the mean
                         and stdDev of the local context (for a window of 5, it
                         would consider the current value, 2 values before and 2
                         values after)
    """

    # Warn user that normalizing a second time nullifies the first normalization
    if globalZNormalization is True and localZNormalizationWindowSize > 0:
        raise errors.NormalizationException()

    castDataList = cast(List[Tuple[float, ...]], dataList)
    if globalZNormalization is True:
        if doPitch:
            castDataList = my_math.znormalizeSpeakerData(castDataList, 1, True)
        else:
            castDataList = my_math.znormalizeSpeakerData(castDataList, 2, True)

    # Raw values should have 0 filtered; normalized values are centered around 0, so don't filter
    filterZeroFlag = not globalZNormalization

    tg = textgrid.openTextgrid(tgFN, False)
    if not isinstance(tg.tierDict[tierName], textgrid.IntervalTier):
        raise errors.IncompatibleTierError(tg.tierDict[tierName])

    tier = cast(textgrid.IntervalTier, tg.tierDict[tierName])
    piData = tier.getValuesInIntervals(castDataList)

    outputList: List[List[float]] = []
    for interval, entryList in piData:
        label = interval[0]
        if doPitch:
            tmpValList = [f0Val for _, f0Val, _ in entryList]
            f0Measures = getPitchMeasures(
                tmpValList, tgFN, label, medianFilterWindowSize, filterZeroFlag
            )
            outputList.append(list(f0Measures))
        else:
            tmpValList = [intensityVal for _, _, intensityVal in entryList]

            if filterZeroFlag:
                tmpValList = [
                    intensityVal for intensityVal in tmpValList if intensityVal != 0.0
                ]

            rmsIntensity = 0.0
            if len(tmpValList) != 0:
                rmsIntensity = my_math.rms(tmpValList)
            outputList.append(
                [
                    rmsIntensity,
                ]
            )

    # Locally normalize the output
    if localZNormalizationWindowSize > 0 and len(outputList) > 0:
        for colI in range(len(outputList[0])):
            featValList = [row[colI] for row in outputList]

            featValList = my_math.znormWindowFilter(
                featValList, localZNormalizationWindowSize, True, True
            )
            if len(featValList) != len(outputList):  # This should hopefully not happen
                raise errors.UnexpectedError(
                    "Lists must be of the same length but are not: "
                    f"({len(featValList)}), ({len(outputList)})"
                )

            for i, val in enumerate(featValList):
                outputList[i][colI] = val

    return [tuple(row) for row in outputList]


def getPitchMeasures(
    f0Values: List[float],
    name: str = None,
    label: str = None,
    medianFilterWindowSize: int = None,
    filterZeroFlag: bool = False,
) -> Tuple[float, float, float, float, float, float]:
    """
    Get various measures (min, max, etc) for the passed in list of pitch values

    name is the name of the file.  Label is the label of the current interval.
    Both of these labels are only used debugging and can be ignored if desired.
    medianFilterWindowSize: None -> no median filtering
    filterZeroFlag:True -> zero values are removed
    """

    if name is None:
        name = UNSPECIFIED
    if label is None:
        label = UNSPECIFIED

    if medianFilterWindowSize is not None:
        f0Values = my_math.medianFilter(
            f0Values, medianFilterWindowSize, useEdgePadding=True
        )

    if filterZeroFlag:
        f0Values = [f0Val for f0Val in f0Values if int(f0Val) != 0]

    if len(f0Values) == 0:
        myStr = f"No pitch data for file: {name}, label: {label}"
        print(myStr.encode("ascii", "replace"))
        counts = 0.0
        meanF0 = 0.0
        maxF0 = 0.0
        minF0 = 0.0
        rangeF0 = 0.0
        variance = 0.0
        std = 0.0
    else:
        counts = float(len(f0Values))
        meanF0 = sum(f0Values) / counts
        maxF0 = max(f0Values)
        minF0 = min(f0Values)
        rangeF0 = maxF0 - minF0

        variance = sum([(val - meanF0) ** 2 for val in f0Values]) / counts
        std = math.sqrt(variance)

    return (meanF0, maxF0, minF0, rangeF0, variance, std)


def detectPitchErrors(
    pitchList: List[Tuple[float, float]],
    maxJumpThreshold: float = 0.70,
    tgToMark: Optional[textgrid.Textgrid] = None,
) -> Tuple[List[Point], Optional[textgrid.Textgrid]]:
    """
    Detect pitch halving and doubling errors.

    If a textgrid is passed in, it adds the markings to the textgrid
    """
    if maxJumpThreshold < 0 or maxJumpThreshold > 1:
        raise errors.ArgumentError(
            f"'maxJumpThreshold' must be between 0 and 1.  Was given ({maxJumpThreshold})"
        )

    tierName = _PITCH_ERROR_TIER_NAME
    if tgToMark is not None and tierName in tgToMark.tierNameList:
        raise errors.ArgumentError(
            f"Tier name '{tierName}' is already in provided textgrid"
        )

    errorList = []
    for i in range(1, len(pitchList)):
        lastPitch = pitchList[i - 1][1]
        currentPitch = pitchList[i][1]

        ceilingCutoff = currentPitch / maxJumpThreshold
        floorCutoff = currentPitch * maxJumpThreshold
        if (lastPitch <= floorCutoff) or (lastPitch >= ceilingCutoff):
            currentTime = pitchList[i][0]
            errorList.append(Point(currentTime, str(currentPitch / lastPitch)))

    if tgToMark is not None:
        pointTier = textgrid.PointTier(
            tierName, errorList, tgToMark.minTimestamp, tgToMark.maxTimestamp
        )
        tgToMark.addTier(pointTier)

    return errorList, tgToMark
