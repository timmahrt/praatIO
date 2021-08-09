"""
Functions for reading, writing, querying, and manipulating audio.

see **examples/anonymize_recording.py**, **examples/delete_vowels.py**,
and **examples/extract_subwavs.py**
"""

import math
import wave
import struct
import copy
from typing import List, Tuple
from abc import ABC, abstractmethod

from typing_extensions import Literal, Final

from praatio.utilities import errors
from praatio.utilities import utils

sampWidthDict: Final = {1: "b", 2: "h", 4: "i", 8: "q"}


class AudioDeletion:
    SHRINK: Final = "shrink"
    SILENCE: Final = "silence"
    SINE_WAVE: Final = "sine wave"


_KEEP: Final = "keep"
_DELETE: Final = "delete"

ZERO_CROSSING_TIMESTEP: Final = 0.002


def samplesAsNums(waveData, sampleWidth: int) -> Tuple[int, ...]:
    """Convert samples of a python wave object from bytes to numbers"""
    if len(waveData) == 0:
        raise errors.EndOfAudioData()

    byteCode = sampWidthDict[sampleWidth]
    actualNumFrames = int(len(waveData) / float(sampleWidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, waveData)

    return audioFrameList


def numsAsSamples(sampleWidth: int, numList: List[int]) -> bytes:
    """Convert audio data from numbers to bytes"""
    byteCode = sampWidthDict[sampleWidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)

    return byteStr


def getDuration(wavFN: str) -> float:
    return WavQueryObj(wavFN).getDuration()


def getMaxAmplitude(sampleWidth: int) -> int:
    """Gets the maximum possible amplitude for a given sample width"""
    return 2 ** (sampleWidth * 8 - 1) - 1


def generateSineWave(
    duration: float, freq: int, samplingFreq: int, amplitude: float
) -> List[int]:
    nSamples = int(duration * samplingFreq)
    wavSpec = 2 * math.pi * freq / float(samplingFreq)
    sinWave = [int(amplitude * math.sin(wavSpec * i)) for i in range(nSamples)]
    return sinWave


def generateSilence(duration: float, samplingFreq: int) -> Tuple[int, ...]:
    silence = (0,) * int(duration * samplingFreq)
    return silence


def extractSubwav(fn: str, outputFN: str, startT: float, endT: float) -> None:
    audioObj = openAudioFile(
        fn,
        [
            (startT, endT, ""),
        ],
        doShrink=True,
    )
    audioObj.save(outputFN)


class AbstractWav(ABC):
    def __init__(self, params):
        self.params = params

        self.nchannels = params[0]
        self.sampwidth = params[1]
        self.framerate = params[2]
        self.nframes = params[3]
        self.comptype = params[4]
        self.compname = params[5]

    def findNearestZeroCrossing(
        self, targetTime: float, timeStep: float = ZERO_CROSSING_TIMESTEP
    ) -> float:
        """
        Finds the nearest zero crossing at the given time in an audio file

        Looks both before and after the timeStamp
        """

        leftStartTime = rightStartTime = targetTime
        fileDuration = self.getDuration()

        # Find zero crossings
        smallestLeft = None
        smallestRight = None
        while True:
            try:
                timeStamp = None
                if leftStartTime > 0:
                    timeStamp = self.findNextZeroCrossing(
                        leftStartTime, timeStep, reverse=True
                    )
            except errors.FindZeroCrossingError:
                pass
            else:
                smallestLeft = timeStamp

            try:
                timestamp = None
                if rightStartTime < fileDuration:
                    timestamp = self.findNextZeroCrossing(
                        rightStartTime, timeStep, reverse=False
                    )
            except errors.FindZeroCrossingError:
                pass
            else:
                smallestRight = timestamp

            if smallestLeft is not None or smallestRight is not None:
                break
            elif leftStartTime < 0 and rightStartTime > fileDuration:
                raise (errors.FindZeroCrossingError(0, fileDuration))
            else:
                leftStartTime -= timeStep
                rightStartTime += timeStep

        if smallestLeft is not None:
            leftDiff = targetTime - smallestLeft

        if smallestRight is not None:
            rightDiff = smallestRight - targetTime

        # Is left or right smaller?
        if smallestLeft is None:
            zeroCrossingTime = smallestRight
        elif smallestRight is None:
            zeroCrossingTime = smallestLeft
        elif leftDiff <= rightDiff:
            zeroCrossingTime = smallestLeft
        elif leftDiff > rightDiff:
            zeroCrossingTime = smallestRight

        if zeroCrossingTime is None:
            raise (errors.FindZeroCrossingError(0, fileDuration))

        return zeroCrossingTime

    def findNextZeroCrossing(
        self,
        targetTime: float,
        timeStep: float = ZERO_CROSSING_TIMESTEP,
        reverse: bool = False,
    ) -> float:
        """
        Finds the nearest zero crossing, searching in one direction

        Can do a 'reverse' search by setting reverse to True.  In that case,
        the sample list is searched from back to front.

        targetTime is the startTime if reverse=False and
            the endTime if reverse=True
        """

        startTime = targetTime
        if reverse is True:
            startTime = targetTime - timeStep

        # Don't read over the edges
        if startTime < 0:
            timeStep = startTime + timeStep
            startTime = 0
        elif startTime + timeStep > self.getDuration():
            timeStep = self.getDuration() - startTime

        endTime = startTime + timeStep

        # 1 Get the acoustic information and the sign for each sample
        frameList = self.getSamples(startTime, endTime)
        signList = [utils.sign(val) for val in frameList]

        # 2 did signs change?
        changeList = [signList[i] != signList[i + 1] for i in range(len(frameList) - 1)]

        # 3 get samples where signs changed
        # (iterate backwards if reverse is true)
        if reverse is True:
            start = len(changeList) - 1
            end = 0
            step = -1
        else:
            start = 0
            end = len(changeList) - 1
            step = 1

        changeIndexList = [i for i in range(start, end, step) if changeList[i] == 1]

        # 4 return the zeroed frame closest to starting point
        try:
            zeroedFrame = changeIndexList[0]
        except IndexError:
            raise (errors.FindZeroCrossingError(startTime, endTime))

        # We found the zero by comparing points to the point adjacent to them.
        # It is possible the adjacent point is closer to zero than this one,
        # in which case, it is the better zeroedI
        if abs(frameList[zeroedFrame]) > abs(frameList[zeroedFrame + 1]):
            zeroedFrame = zeroedFrame + 1

        adjustTime = zeroedFrame / float(self.framerate)

        return startTime + adjustTime

    @abstractmethod
    def getDuration(self) -> float:
        pass

    @abstractmethod
    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:
        pass


class WavQueryObj(AbstractWav):
    """
    A class for getting information about a wave file

    The wave file is never loaded--we only keep a reference to the
    fd.  All operations on WavQueryObj are fast.  WavQueryObjs don't
    (shouldn't) change state.  For doing multiple modifications,
    use a WavObj.
    """

    def __init__(self, fn: str):
        self.audiofile = wave.open(fn, "r")
        super(WavQueryObj, self).__init__(self.audiofile.getparams())

    def concatenate(
        self, targetFrames: List[int], outputFN: str, prepend: bool = False
    ) -> None:
        sourceFrames = self.getFrames()

        if prepend is True:
            newFrames = targetFrames + sourceFrames
        else:
            newFrames = sourceFrames + targetFrames

        self.outputModifiedWav(newFrames, outputFN)

    def getDuration(self) -> float:
        duration = float(self.nframes) / self.framerate
        return duration

    def getFrames(self, startTime: float = None, endTime: float = None):
        """
        Get frames with respect to time
        """
        if startTime is None:
            startTime = 0
        startFrame = int(startTime * float(self.framerate))

        if endTime is not None:
            duration = endTime - startTime
            nFrames = int(self.framerate * duration)
        else:
            nFrames = int(self.nframes - startFrame)

        self.audiofile.setpos(startFrame)
        frames = self.audiofile.readframes(nFrames)

        return frames

    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:

        frames = self.getFrames(startTime, endTime)
        audioFrameList = samplesAsNums(frames, self.sampwidth)

        return audioFrameList

    def deleteWavSections(
        self,
        outputFN: str,
        keepList: List[Tuple[float, float, str]] = None,
        deleteList: List[Tuple[float, float, str]] = None,
        operation: Literal["shrink", "silence", "sine wave"] = AudioDeletion.SHRINK,
        sineWaveAmplitude: float = None,
    ):
        """
        Remove from the audio all of the intervals

        DeleteList can easily be constructed from a textgrid tier
        e.g. deleteList = tg.tierDict["targetTier"].entryList

        operation: "shrink" to shrink the file length or "silence" or
                   "sine wave" to replace the segment with silence or
                   a sine wave
        sineWaveAmplitude: if None and operation is "sine wave"
                           use max amplitude.
        """
        operationOptions = [
            AudioDeletion.SHRINK,
            AudioDeletion.SILENCE,
            AudioDeletion.SINE_WAVE,
        ]
        if operation not in operationOptions:
            raise errors.WrongOption("operation", operation, operationOptions)

        duration = float(self.nframes) / self.framerate

        if (keepList is not None and deleteList is not None) or (
            keepList is None and deleteList is None
        ):
            raise errors.ArgumentError(
                "You must specify 'keepList' or 'deleteList' but not both."
            )

        if keepList is None and deleteList is not None:
            computedKeepList = utils.invertIntervalList(
                [(row[0], row[1]) for row in deleteList], duration
            )
            computedDeleteList = []
        elif keepList is not None and deleteList is None:
            computedKeepList = []
            computedDeleteList = utils.invertIntervalList(
                [(row[0], row[1]) for row in keepList], duration
            )
        keepList = [(row[0], row[1], _KEEP) for row in computedKeepList]
        deleteList = [(row[0], row[1], _DELETE) for row in computedDeleteList]
        iterList = sorted(keepList + deleteList)

        zeroBinValue = struct.pack(sampWidthDict[self.sampwidth], 0)

        # Grab the sections to be kept
        audioFrames = b""
        for start, end, label in iterList:
            diff = end - start

            if label == _KEEP:
                self.audiofile.setpos(int(self.framerate * start))
                frames = self.audiofile.readframes(int(self.framerate * diff))
                audioFrames += frames

            # If we are not keeping a region and we're not shrinking the
            # duration, fill in the deleted portions with zeros
            elif label == _DELETE and operation == AudioDeletion.SILENCE:
                frames = zeroBinValue * int(self.framerate * diff)
                audioFrames += frames
            # Or fill it with a sine wave
            elif label == _DELETE and operation == AudioDeletion.SINE_WAVE:
                frequency = 200
                if sineWaveAmplitude is None:
                    sineWaveAmplitude = getMaxAmplitude(self.sampwidth)
                sineWave = generateSineWave(
                    diff, frequency, self.framerate, sineWaveAmplitude
                )
                frames = numsAsSamples(self.sampwidth, sineWave)
                audioFrames += frames

            self.outputModifiedWav(audioFrames, outputFN)

    def outputModifiedWav(self, audioFrames: bytes, outputFN: str):
        """
        Output frames using the same parameters as this WavQueryObj
        """

        # Output resulting wav file
        outParams = [
            self.nchannels,
            self.sampwidth,
            self.framerate,
            len(audioFrames),
            self.comptype,
            self.compname,
        ]

        outWave = wave.open(outputFN, "w")
        outWave.setparams(outParams)
        outWave.writeframes(audioFrames)


class WavObj(AbstractWav):
    """
    A class for manipulating audio files

    The wav file is represented by its wavform as a series of signed
    integers.  This can be very slow and take up lots of memory with
    large files.
    """

    def __init__(self, audioSamples: Tuple[int, ...], params: dict):
        self.audioSamples = audioSamples
        super(WavObj, self).__init__(params)

    def getIndexAtTime(self, startTime: float):
        return int(startTime * self.framerate)

    def insertSilence(self, startTime: float, silenceDuration: float):
        audioSamples = generateSilence(silenceDuration, self.framerate)
        self.insert(startTime, audioSamples)

    def insert(self, startTime: float, audioSamples: Tuple[int, ...]):
        i = self.getIndexAtTime(startTime)
        self.audioSamples = self.audioSamples[:i] + audioSamples + self.audioSamples[i:]

    def deleteSegment(self, startTime: float, endTime: float):
        i = self.getIndexAtTime(startTime)
        j = self.getIndexAtTime(endTime)
        self.audioSamples = self.audioSamples[:i] + self.audioSamples[j:]

    def getDuration(self):
        return float(len(self.audioSamples)) / self.framerate

    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:
        i = self.getIndexAtTime(startTime)
        j = self.getIndexAtTime(endTime)
        return tuple(self.audioSamples[i:j])

    def getSubsegment(self, startTime: float, endTime: float) -> "WavObj":
        samples = self.getSamples(startTime, endTime)
        return WavObj(samples, self.params)

    def new(self):
        return copy.deepcopy(self)

    def save(self, outputFN: str):
        # Output resulting wav file
        outParams = [
            self.nchannels,
            self.sampwidth,
            self.framerate,
            len(self.audioSamples),
            self.comptype,
            self.compname,
        ]

        byteCode = sampWidthDict[self.sampwidth]
        byteStr = struct.pack(
            "<" + byteCode * len(self.audioSamples), *self.audioSamples
        )

        outWave = wave.open(outputFN, "w")
        outWave.setparams(outParams)
        outWave.writeframes(byteStr)


def openAudioFile(
    fn: str,
    keepList: List[Tuple[float, float, str]] = None,
    deleteList: List[Tuple[float, float, str]] = None,
    doShrink: bool = True,
) -> WavObj:
    """
    Remove from the audio all of the intervals

    keepList - specifies the segments to keep; by default, everything is kept
    doShrink - if False, segments not kept are replaced by silence
    """

    audiofile = wave.open(fn, "r")

    params = audiofile.getparams()
    sampwidth = params[1]
    framerate = params[2]
    nframes = params[3]

    duration = nframes / float(framerate)

    if keepList is not None and deleteList is not None:
        raise errors.ArgumentError(
            "You cannot specify both 'keepList' or 'deleteList'."
        )

    if keepList is None and deleteList is not None:
        computedKeepList = utils.invertIntervalList(
            [(start, end) for start, end, _ in deleteList], duration
        )
        computedDeleteList = []
    elif deleteList is None and keepList is not None:
        computedKeepList = []
        computedDeleteList = utils.invertIntervalList(
            [(start, end) for start, end, _ in keepList], duration
        )
    else:
        computedKeepList = [
            (0, duration),
        ]
        computedDeleteList = []

    keepList = [(row[0], row[1], _KEEP) for row in computedKeepList]
    deleteList = [(row[0], row[1], _DELETE) for row in computedDeleteList]
    iterList = sorted(keepList + deleteList)

    # Grab the sections to be kept
    audioSampleList: List = []
    byteCode = sampWidthDict[sampwidth]
    for start, end, label in iterList:
        diff = end - start

        if label == _KEEP:
            audiofile.setpos(int(framerate * start))
            frames = audiofile.readframes(int(framerate * diff))

            actualNumFrames = int(len(frames) / float(sampwidth))
            audioSamples = struct.unpack("<" + byteCode * actualNumFrames, frames)
            audioSampleList.extend(audioSamples)

        # If we are not keeping a region and we're not shrinking the
        # duration, fill in the deleted portions with zeros
        elif label == _DELETE and doShrink is False:
            zeroPadding = [0] * int(framerate * diff)
            audioSampleList.extend(zeroPadding)

    return WavObj(tuple(audioSampleList), params)
