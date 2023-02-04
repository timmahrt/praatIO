"""
Automatically segments an audio file based on silence.

Marks an utterance for speech and silence.  Then, via
markTranscriptForAnnotations, chunks those segments into small,
manageable chunks.  The code assumes that the speaker is
talking most of the time.

Probably only useful in limited circumstances.
"""

import os
from os.path import join
import math

from praatio import textgrid
from praatio import praat_scripts
from praatio.utilities import utils


def markTranscriptForAnnotations(tgFN, tierName, outputTGFN, proportion=1 / 5.0):
    """
    Prep a noisy silence annotation for an annotation task

    Voice activity detectors are liable to segment speech into very small
    chunks (fragments of speech and silence).  The point of this code is
    to segment a recording into larger units that could be used in a
    speech transcription task.

    Assumes the speaker is speaking for most of the recording.
    """
    tg = textgrid.openTextgrid(tgFN, False)

    duration = tg.maxTimestamp
    numEntries = int(math.ceil(duration * proportion))
    entryList = tg.getTier(tierName).entryList

    # Get all silent intervals
    entryList = [
        (end - start, start, end, label)
        for start, end, label in entryList
        if label == "silent"
    ]

    # Remove silent intervals at the start or end of the file
    entryList = [entry for entry in entryList if entry[1] != 0 and entry[2] != duration]

    # Put longest intervals first
    entryList.sort(reverse=True)

    # Get the mid point of the longest n intervals and convert them
    # into intervals to be transcribed
    entryList = entryList[:numEntries]
    pointList = [start + ((end - start) / 2.0) for _, start, end, _ in entryList]
    pointList.sort()

    pointList = [0.0] + pointList + [duration]

    newEntryList = []
    for i in range(len(pointList) - 1):
        newEntryList.append((pointList[i], pointList[i + 1], "%d" % i))

    outputTG = textgrid.Textgrid()
    tier = textgrid.IntervalTier("toTranscribe", newEntryList, 0, duration)
    outputTG.addTier(tier)

    outputTG.save(outputTGFN, "short_textgrid", True)


def autoSegmentSpeech(praatEXE, inputWavPath, rawTGPath, finalTGPath):
    utils.makeDir(rawTGPath)
    utils.makeDir(finalTGPath)

    for fn in os.listdir(inputWavPath):
        if ".wav" not in fn:
            continue
        name = os.path.splitext(fn)[0]
        tgFn = name + ".TextGrid"
        praat_scripts.annotateSilences(
            praatEXE, join(inputWavPath, fn), join(rawTGPath, tgFn)
        )

    for fn in os.listdir(rawTGPath):
        if ".TextGrid" not in fn:
            continue
        markTranscriptForAnnotations(
            join(rawTGPath, fn), "silences", join(finalTGPath, fn)
        )


# 2021/07/09 I tried to run this with relative paths
# but it didn't work.  Using absolute paths did though.
_praatEXE = r"C:\praat.exe"
_praatEXE = "/Applications/Praat.app/Contents/MacOS/Praat"
_root = "/Users/tmahrt/Dropbox/workspace/praatIO/examples/files"
_inputWavPath = _root
_rawTGPath = join(_root, "silence_marked_textgrids")
_finalTGPath = join(_root, "ready-to-transcribe_textgrids")
autoSegmentSpeech(_praatEXE, _inputWavPath, _rawTGPath, _finalTGPath)
