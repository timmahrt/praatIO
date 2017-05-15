'''
Created on Oct 13, 2016

@author: Tim

Marks an utterance for speech and silence.  Then, via
markTranscriptForAnnotations, chunks those segments into small,
manageable chunks.  The code assumes that the speaker is
talking most of the time.
'''

from os.path import join
import math

from praatio import tgio
from praatio import praat_scripts
from praatio.utilities import utils


def markTranscriptForAnnotations(tgFN, tierName, outputTGFN,
                                 proportion=1 / 5.0):
    '''
    Prep a noisy silence annotation for an annotation task
    
    Voice activity detectors are liable to segment speech into very small
    chunks (fragments of speech and silence).  The point of this code is
    to segment a recording into larger units that could be used in a
    speech transcription task.
    
    Assumes the speaker is speaking for most of the recording.
    '''
    tg = tgio.openTextgrid(tgFN)
    
    duration = tg.maxTimestamp
    numEntries = int(math.ceil(duration * proportion))
    entryList = tg.tierDict[tierName].entryList
    
    # Get all silent intervals
    entryList = [(stop - start, start, stop, label)
                 for start, stop, label in entryList
                 if label == "silent"]
    
    # Remove silent intervals at the start or end of the file
    entryList = [entry for entry in entryList
                 if entry[1] != 0 and entry[2] != duration]
    
    # Put longest intervals first
    entryList.sort(reverse=True)
    
    # Get the mid point of the longest n intervals and convert them
    # into intervals to be transcribed
    entryList = entryList[:numEntries]
    pointList = [start + ((stop - start) / 2.0)
                 for _, start, stop, _ in entryList]
    pointList.sort()
    
    pointList = [0.0, ] + pointList + [duration, ]
    
    newEntryList = []
    for i in range(len(pointList) - 1):
        newEntryList.append((pointList[i], pointList[i + 1], "%d" % i))
    
    outputTG = tgio.Textgrid()
    tier = tgio.IntervalTier("toTranscribe", newEntryList, 0, duration)
    outputTG.addTier(tier)
    
    outputTG.save(outputTGFN)


def autoSegmentSpeech(praatEXE, inputWavPath, rawTGPath, finalTGPath):
    
    utils.makeDir(finalTGPath)
    
    praat_scripts.annotateSilences(praatEXE, inputWavPath, rawTGPath)
    
    for tgFN in utils.findFiles(rawTGPath, filterExt=".TextGrid"):
        markTranscriptForAnnotations(join(rawTGPath, tgFN),
                                     "silences",
                                     join(finalTGPath, tgFN))


_praatEXE = r"C:\praat.exe"
_root = join(".", "files")
_inputWavPath = _root
_rawTGPath = join(_root, "silence_marked_textgrids")
_finalTGPath = join(_root, "ready-to-transcribe_textgrids")
autoSegmentSpeech(_praatEXE, _inputWavPath, _rawTGPath, _finalTGPath)
