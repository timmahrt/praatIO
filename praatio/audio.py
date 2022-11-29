"""
Functions for reading, writing, querying, and manipulating audio.

see **examples/anonymize_recording.py**, **examples/delete_vowels.py**,
and **examples/extract_subwavs.py**
"""

import math
import wave
import struct
import copy
from typing import List, Tuple, Optional, Callable
from abc import ABC, abstractmethod
from functools import partial

from typing_extensions import Final

from praatio.utilities import errors
from praatio.utilities import utils

sampleWidthDict: Final = {1: "b", 2: "h", 4: "i", 8: "q"}


class AudioDeletion:
    SHRINK: Final = "shrink"
    SILENCE: Final = "silence"
    SINE_WAVE: Final = "sine wave"


_KEEP: Final = "keep"
_DELETE: Final = "delete"

ZERO_CROSSING_TIMESTEP: Final = 0.002
DEFAULT_SINE_FREQUENCY = 200
NUM_BITS_IN_A_BYTE = 8


def calculateMaxAmplitude(sampleWidth: int) -> int:
    """Gets the largest possible amplitude representable by a given sample width

    The formula is 2^(n-1) - 1 where n is the number of bits
    - the first -1 is because the result is signed
    - the second -1 is because the value is 0 based
    e.g. if n=3 then 2^(3-1)-1 => 3
         if n=4 then 2^(4-1)-1 => 7

    Args:
        sampleWidth: the width in bytes of a sample in the wave file

    Returns:
        An integer
    """
    return 2 ** (sampleWidth * NUM_BITS_IN_A_BYTE - 1) - 1


def convertFromBytes(byteStr: bytes, sampleWidth: int) -> Tuple[int, ...]:
    """Convert frames of a python wave object from bytes to numbers"""
    if len(byteStr) == 0:
        raise errors.EndOfAudioData()

    byteCode = sampleWidthDict[sampleWidth]
    actualNumFrames = int(len(byteStr) / float(sampleWidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, byteStr)

    return audioFrameList


def convertToBytes(numList: Tuple[int, ...], sampleWidth: int) -> bytes:
    """Convert frames of a python wave object from numbers to bytes"""
    byteCode = sampleWidthDict[sampleWidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)

    return byteStr


def extractSubwav(fn: str, outputFN: str, startTime: float, endTime: float) -> None:
    wav = QueryWav(fn)
    frames = wav.getFrames(startTime, endTime)
    wav.outputFrames(frames, outputFN)


def getDuration(fn: str) -> float:
    return QueryWav(fn).duration


def readFramesAtTime(
    audiofile: wave.Wave_read, startTime: float, endTime: float
) -> bytes:
    params = audiofile.getparams()
    frameRate = params[2]

    audiofile.setpos(round(frameRate * startTime))
    frames = audiofile.readframes(round(frameRate * (endTime - startTime)))

    return frames


def readFramesAtTimes(
    audiofile: wave.Wave_read,
    keepList: List[Tuple[float, float]] = None,
    deleteList: List[Tuple[float, float]] = None,
    replaceFunc: Optional[Callable[[float], bytes]] = None,
) -> bytes:
    """Reads an audio file into memory, with some configuration

    Args:
        audiofile: the time to get the interval from
        keepList: duration of the interval
        deleteList: the maximum allowed time
        replaceFunc: is the interval before or after the targetTime?

    Returns:
        A bytestring of the loaded audio file

    Raises:
        ArgumentError: The timestamps in keepList or deleteList exceed the audio duration
    """
    params = audiofile.getparams()
    frameRate = params[2]
    nframes = params[3]

    duration = nframes / float(frameRate)
    markedIntervals = _computeKeepDeleteIntervals(0.0, duration, keepList, deleteList)

    if markedIntervals[-1][1] > duration:
        raise errors.ArgumentError(
            "Timestamps in keepList and deleteList cannot exceed wav file duration"
        )

    # Grab the sections to be kept
    audioFrames: bytes = b""
    for start, end, label in markedIntervals:
        if label == _KEEP:
            audioFrames += readFramesAtTime(audiofile, start, end)

        # If we are not keeping a region and we're not shrinking the
        # duration, fill in the deleted portions with zeros
        elif label == _DELETE and replaceFunc:
            audioFrames += replaceFunc(end - start)

    return audioFrames


class AbstractWav(ABC):
    def __init__(self, params: List):
        self.params = params

        self.nchannels: int = params[0]
        self.sampleWidth: int = params[1]
        self.frameRate: int = params[2]
        self.nframes: int = params[3]
        self.comptype = params[4]
        self.compname = params[5]

    def _iterZeroCrossings(
        self,
        start: float,
        withinThreshold,
        step: float = ZERO_CROSSING_TIMESTEP,
        reverse: bool = False,
    ) -> Optional[float]:
        try:
            if withinThreshold(start):
                startTime, endTime = utils.getInterval(
                    start, self.duration, step, reverse
                )
                samples = self.getSamples(startTime, endTime)

                return _findNextZeroCrossing(startTime, endTime, samples, reverse)
        except errors.FindZeroCrossingError:
            pass

        return None

    @property
    @abstractmethod
    def duration(self) -> float:
        pass

    def findNearestZeroCrossing(
        self, targetTime: float, timeStep: float = ZERO_CROSSING_TIMESTEP
    ) -> float:
        """Finds the nearest zero crossing at the given time in an audio file

        Looks both before and after the timeStamp
        """

        leftStartTime = rightStartTime = targetTime
        fileDuration = self.duration

        # Find zero crossings
        smallestLeft = None
        smallestRight = None
        while True:
            smallestLeft = self._iterZeroCrossings(
                leftStartTime, lambda x: x > 0, timeStep, True
            )
            smallestRight = self._iterZeroCrossings(
                rightStartTime, lambda x: x < fileDuration, timeStep, False
            )

            if smallestLeft is not None or smallestRight is not None:
                break
            # TODO: I think this case shouldn't be possible
            elif leftStartTime < 0 and rightStartTime > fileDuration:
                raise (errors.FindZeroCrossingError(0, fileDuration))
            # TODO: I think this case shouldn't be possible
            else:
                leftStartTime -= timeStep
                rightStartTime += timeStep

        return utils.chooseClosestTime(
            targetTime, smallestLeft, smallestRight, fileDuration
        )

    @abstractmethod
    def getFrames(self, startTime: float, endTime: float) -> bytes:
        pass

    @abstractmethod
    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:
        pass

    def outputFrames(self, frames: bytes, outputFN: str) -> None:
        """Output frames using the same parameters as this Wav"""
        outWave = wave.open(outputFN, "w")
        outWave.setparams(
            [
                self.nchannels,
                self.sampleWidth,
                self.frameRate,
                len(frames),
                self.comptype,
                self.compname,
            ]
        )
        outWave.writeframes(frames)


class QueryWav(AbstractWav):
    """A class for getting information about a wave file

    The wave file is never loaded--we only keep a reference to the
    file descriptor.  All operations on QueryWavs are fast.
    QueryWavs don't (shouldn't) change state.  For doing
    multiple modifications, use a Wav.
    """

    def __init__(self, fn: str):
        self.audiofile = wave.open(fn, "r")
        super(QueryWav, self).__init__(self.audiofile.getparams())

    @property
    def duration(self) -> float:
        duration = float(self.nframes) / self.frameRate
        return duration

    def getFrames(self, startTime: float = None, endTime: float = None) -> bytes:
        if startTime is None:
            startTime = 0

        if endTime is None:
            endTime = self.duration

        return readFramesAtTime(self.audiofile, startTime, endTime)

    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:

        frames = self.getFrames(startTime, endTime)
        audioFrameList = convertFromBytes(frames, self.sampleWidth)

        return audioFrameList


class Wav(AbstractWav):
    """A class for manipulating audio files

    The wav file is represented by its wavform as a series of signed
    integers.  This can be very slow and take up lots of memory with
    large files.
    """

    def __init__(self, frames: bytes, params: List):
        self.frames = frames
        super(Wav, self).__init__(params)

    def _getIndexAtTime(self, startTime: float) -> int:
        return round(startTime * self.frameRate)

    @classmethod
    def open(cls, fn: str) -> "Wav":
        wav = wave.open(fn, "r")
        audioFrames = readFramesAtTime(wav, startTime=0, endTime=getDuration(fn))
        return Wav(audioFrames, wav.getparams())

    def concatenate(self, frames: bytes) -> None:
        self.frames += frames

    def deleteSegment(self, startTime: float, endTime: float) -> None:
        i = self._getIndexAtTime(startTime)
        j = self._getIndexAtTime(endTime)
        self.frames = self.frames[:i] + self.frames[j:]

    @property
    def duration(self) -> float:
        return len(self.frames) / self.frameRate

    def getFrames(self, startTime: float, endTime: float) -> bytes:
        i = self._getIndexAtTime(startTime)
        j = self._getIndexAtTime(endTime)
        return self.frames[i:j]

    def getSamples(self, startTime: float, endTime: float) -> Tuple[int, ...]:
        frames = self.getFrames(startTime, endTime)
        return convertFromBytes(frames, self.sampleWidth)

    def getSubwav(self, startTime: float, endTime: float) -> "Wav":
        frames = self.getFrames(startTime, endTime)
        return Wav(frames, self.params)

    def insert(self, startTime: float, frames: bytes) -> None:
        i = self._getIndexAtTime(startTime)
        self.frames = self.frames[:i] + frames + self.frames[i:]

    def new(self) -> "Wav":
        return copy.deepcopy(self)

    def replaceSegment(self, startTime: float, endTime: float, frames: bytes):
        self.deleteSegment(startTime, endTime)
        self.insert(startTime, frames)

    def save(self, outputFN: str) -> None:
        outWave = wave.open(outputFN, "w")
        outWave.setparams(
            [
                self.nchannels,
                self.sampleWidth,
                self.frameRate,
                len(self.frames),
                self.comptype,
                self.compname,
            ]
        )
        outWave.writeframes(self.frames)


class AudioGenerator:
    def __init__(self, sampleWidth, frameRate):
        self.sampleWidth: int = sampleWidth
        self.frameRate: int = frameRate

    def buildSineWaveGenerator(self, frequency, amplitude) -> Callable[[float], bytes]:
        """Returns a function that takes a duration and returns a generated sine wave"""
        return partial(
            self.generateSineWave,
            frequency=frequency,
            frameRate=self.frameRate,
            sampleWidth=self.sampleWidth,
            amplitude=amplitude,
        )

    def generateSineWave(
        self,
        duration: float,
        frequency: int,
        amplitude: Optional[float] = None,
    ) -> bytes:
        if amplitude is None:
            amplitude = calculateMaxAmplitude(self.sampleWidth)

        nSamples = round(duration * self.frameRate)
        wavSpec = 2 * math.pi * frequency / float(self.frameRate)
        sinWaveNums = [
            round(amplitude * math.sin(wavSpec * i)) for i in range(nSamples)
        ]
        return convertToBytes(tuple(sinWaveNums), self.sampleWidth)

    def generateSilence(self, duration: float) -> bytes:
        zeroBinValue = struct.pack(sampleWidthDict[self.sampleWidth], 0)
        return zeroBinValue * round(self.frameRate * duration)


def _findNextZeroCrossing(
    startTime: float,
    endTime: float,
    samples: Tuple[int, ...],
    frameRate: float,
    reverse: bool = False,
) -> float:
    """Finds the nearest zero crossing, searching in one direction

    Can do a 'reverse' search by setting reverse to True.  In that case,
    the sample list is searched from back to front.

    targetTime is the startTime if reverse=False and
        the endTime if reverse=True
    """

    # 1 Get the sign for each sample
    signList = [utils.sign(val) for val in samples]

    # 2 did signs change?
    changeList = [signList[i] != signList[i + 1] for i in range(len(samples) - 1)]

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
    if abs(samples[zeroedFrame]) > abs(samples[zeroedFrame + 1]):
        zeroedFrame = zeroedFrame + 1

    adjustTime = zeroedFrame / float(frameRate)

    return startTime + adjustTime


def _computeKeepDeleteIntervals(
    start: float,
    stop: float,
    keepList: List[Tuple[float, float]] = None,
    deleteList: List[Tuple[float, float]] = None,
) -> List[Tuple[float, float, str]]:
    """Returns a list of intervals, each one labeled 'keep' or 'delete'"""
    if keepList and deleteList:
        raise errors.ArgumentError(
            "You cannot specify both 'keepList' or 'deleteList'."
        )

    elif not keepList and not deleteList:
        computedKeepList = [(start, stop)]
        computedDeleteList = []

    elif deleteList:
        deleteTimestamps = [(interval[0], interval[1]) for interval in deleteList]
        computedKeepList = utils.invertIntervalList(deleteTimestamps, start, stop)
        computedDeleteList = deleteTimestamps

    elif keepList:
        keepTimestamps = [(interval[0], interval[1]) for interval in keepList]
        computedKeepList = keepTimestamps
        computedDeleteList = utils.invertIntervalList(keepTimestamps, start, stop)

    annotatedKeepList = [(start, end, _KEEP) for start, end in computedKeepList]
    annotatedDeleteList = [(start, end, _DELETE) for start, end in computedDeleteList]
    intervals = sorted(annotatedKeepList + annotatedDeleteList)

    return intervals
