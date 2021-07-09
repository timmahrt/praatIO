"""
Python wrappers for various praat scripts contained in /praatScripts.

see **examples/auto_segment_speech.py**, **examples/get_pitch_and_formants.py**,
**klatt_resynthesis.py**
"""

import os
from os.path import join
import io
import csv
from typing import List, Optional, Tuple

from praatio import audio
from praatio import data_points
from praatio.utilities import constants
from praatio.utilities import utils

SILENCE_LABEL = "silent"
SOUND_LABEL = "sound"


def changeGender(
    praatEXE: str,
    wavFN: str,
    outputWavFN: str,
    pitchFloor: float,
    pitchCeiling: float,
    formantShiftRatio: float,
    pitchMedian: float = 0.0,
    pitchRange: float = 1.0,
    duration: float = 1.0,
    scriptFN: Optional[str] = None,
) -> None:
    """
    Changes the speech formants in a file using praat's change gender function

    PitchMedian = 0.0; no change in median pitch
    PitchRange = 1.0; no change in pitch range

    Uses the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__Change_gender___.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "change_gender.praat")

    #  Praat crashes on exit after resynthesis with a klattgrid
    utils.runPraatScript(
        praatEXE,
        scriptFN,
        [
            wavFN,
            outputWavFN,
            pitchFloor,
            pitchCeiling,
            formantShiftRatio,
            pitchMedian,
            pitchRange,
            duration,
        ],
    )


def changeIntensity(
    praatEXE: str,
    wavFN: str,
    outputWavFN: str,
    newIntensity: float,
    scriptFN: Optional[str] = None,
) -> None:
    """
    Changes the intensity of the wavFN (in db)

    Uses the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__Scale_intensity___.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "change_intensity.praat")

    #  Praat crashes on exit after resynthesis with a klattgrid
    utils.runPraatScript(praatEXE, scriptFN, [wavFN, outputWavFN, newIntensity])


def getFormants(
    praatEXE: str,
    inputWavFN: str,
    outputTxtFN: str,
    maxFormant: float,
    stepSize: float = 0.01,
    window_length: float = 0.025,
    preemphasis: float = 50,
    scriptFN: Optional[str] = None,
    undefinedValue: Optional[str] = None,
) -> List:
    """
    Get F1, F2, and F3 for the audio file

    maxFormant = 5500 for females, 5000 for males, <8000 for children

    Uses the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_Formant__burg____.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "get_formants.praat")

    argList = [
        inputWavFN,
        outputTxtFN,
        stepSize,
        maxFormant,
        window_length,
        preemphasis,
        -1,
        -1,
    ]
    utils.runPraatScript(praatEXE, scriptFN, argList)

    # Load the output
    path, fn = os.path.split(outputTxtFN)
    with open(os.path.join(path, fn), "r", encoding="utf-8") as fd:
        csvFile = csv.reader(fd)
        dataList = [row for row in csvFile]

    # The new praat script includes a header
    if dataList[0][0] == "time":
        dataList = dataList[1:]

    # Handle undefined values, convert values to float
    returnList = []
    for row in dataList:
        keep = True
        for i in range(1, 4):
            if "--" in row[i]:
                if undefinedValue is not None:
                    row[i] = undefinedValue
                else:
                    keep = False
                    break

        if keep is True:
            returnList.append([float(val) for val in row])

    return returnList


def getPulses(
    praatEXE: str,
    inputWavFN: str,
    outputPointTierFN: str,
    minPitch: float,
    maxPitch: float,
    scriptFN: Optional[str] = None,
) -> data_points.PointObject1D:
    """
    Gets the pitch/glottal pulses for an audio file.

    Uses the following praat command:
    http://www.fon.hum.uva.nl/praat/manual/Sound___Pitch__To_PointProcess__peaks____.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "get_pulses.praat")

    argList = [inputWavFN, outputPointTierFN, minPitch, maxPitch]
    utils.runPraatScript(praatEXE, scriptFN, argList)

    # Load the output
    pointObj = data_points.open1DPointObject(outputPointTierFN)

    return pointObj


def getSpectralInfo(
    praatEXE: str,
    inputWavFN: str,
    inputTGFN: str,
    outputCSVFN: str,
    tierName: str,
    spectralPower: int = 2,
    spectralMoment: int = 3,
    scriptFN: Optional[str] = None,
) -> Tuple[List, List]:
    """
    Extracts various spectral measures from an audio file

    Measures include: center_of_gravity, standard_deviation
    skewness, kertosis, central_movement

    Uses the following praat command:
    http://www.fon.hum.uva.nl/praat/manual/Spectrum.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "get_spectral_info.praat")

    argList = [
        inputWavFN,
        inputTGFN,
        outputCSVFN,
        tierName,
        spectralPower,
        spectralMoment,
    ]
    utils.runPraatScript(praatEXE, scriptFN, argList)

    # Load the output
    with io.open(outputCSVFN, "r", encoding="utf-8") as fd:
        data = fd.read()

    dataList = data.rstrip().split("\n")
    dataListOfLists = [row.split(",") for row in dataList]
    titleRow, mainDataListOfLists = dataListOfLists[0], dataListOfLists[1:]

    return titleRow, mainDataListOfLists


def resynthesizePitch(
    praatEXE: str,
    inputWavFN: str,
    pitchFN: str,
    outputWavFN: str,
    minPitch: float,
    maxPitch: float,
    scriptFN: Optional[str] = None,
    pointList: Optional[List] = None,
) -> None:
    """
    Resynthesizes the pitch in a wav file with the given pitch contour file

    The pitch track to use can optionally be passed in as pointList.  If
    so, it will be saved as pitchFN for praat to be able to use.

    Uses the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Manipulation.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "resynthesize_pitch.praat")

    if pointList is not None:
        dur = audio.WavQueryObj(inputWavFN).getDuration()
        pointObj = data_points.PointObject2D(
            pointList, constants.DataPointTypes.PITCH, 0, dur
        )
        pointObj.save(pitchFN)

    utils.runPraatScript(
        praatEXE, scriptFN, [inputWavFN, pitchFN, outputWavFN, minPitch, maxPitch]
    )


def resynthesizeDuration(
    praatEXE: str,
    inputWavFN: str,
    durationTierFN: str,
    outputWavFN: str,
    minPitch: float,
    maxPitch: float,
    scriptFN: Optional[str] = None,
) -> None:
    """
    Resynthesizes the duration in a wav file with the given duration tier

    Uses the following praat command:
    https://www.fon.hum.uva.nl/praat/manual/Manipulation.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "resynthesize_duration.praat")

    utils.runPraatScript(
        praatEXE,
        scriptFN,
        [inputWavFN, durationTierFN, outputWavFN, minPitch, maxPitch],
    )


def annotateSilences(
    praatEXE: str,
    inputWavPath: str,
    outputTGPath: str,
    minPitch: float = 100,
    timeStep: float = 0.0,
    silenceThreshold: float = -25.0,
    minSilDur: float = 0.1,
    minSoundDur: float = 0.1,
    silentLabel: str = SILENCE_LABEL,
    soundLabel: str = SOUND_LABEL,
    scriptFN: Optional[str] = None,
) -> None:
    """
    Marks the silences and non-silences of an audio file

    Uses the praat command:
    https://www.fon.hum.uva.nl/praat/manual/Sound__To_TextGrid__silences____.html
    """
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "annotate_silences.praat")

    utils.runPraatScript(
        praatEXE,
        scriptFN,
        [
            inputWavPath,
            outputTGPath,
            minPitch,
            timeStep,
            silenceThreshold,
            minSilDur,
            minSoundDur,
            silentLabel,
            soundLabel,
        ],
    )
