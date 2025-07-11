"""
Functions for reading, writing, querying, and manipulating audio.

see **examples/anonymize_recording.py**, **examples/delete_vowels.py**,
and **examples/extract_subwavs.py**
"""

import math
import wave
import struct
import copy
from typing import List, Sequence, Tuple, Optional, Callable, Iterable
from abc import ABC, abstractmethod
from functools import partial

from typing_extensions import Final

from praatio.utilities import errors
from praatio.utilities import utils

sampleWidthDict: Final = {1: "b", 2: "h", 4: "i", 8: "q"}

_KEEP: Final = "keep"
_DELETE: Final = "delete"

ZERO_CROSSING_TIMESTEP: Final = 0.002
DEFAULT_SINE_FREQUENCY = 200
NUM_BITS_IN_A_BYTE = 8


def _diffBooleans(a: bool, b: bool) -> int:
    if a == b:
        return 0
    elif a is True and b is False:
        return -1

    # For mypy
    # a is False and b is True
    return 1


def _getZeroCrossings(
    samples: Sequence[int], startTime: float, framerate: int
) -> List[float]:
    """
    Given a list of samples, return a list of times where zero-crossings occur.

    Inspired by:
    https://stackoverflow.com/a/44322349
    """
    rightGreater = [val > 0 for val in samples]
    rightComp = [
        _diffBooleans(a, b) for a, b in zip(rightGreater[0::], rightGreater[1::])
    ]

    def getClosest(i):
        # A zero crossing happens between two values (e.g. a change from positive to negative)
        # Choose the smaller of the two values involved
        return min([i, i + 1], key=lambda i: abs(samples[i]))

    zeroCrossings = [getClosest(i) for i in range(len(rightComp)) if rightComp[i] != 0]

    zeroCrossingsInTime = [
        startTime + (zeroI / float(framerate)) for zeroI in zeroCrossings
    ]

    return zeroCrossingsInTime


def calculateMaxAmplitude(sampleWidth: int) -> int:
    """Get the largest possible amplitude representable by a given sample width.

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
    """Convert frames of a python wave object from bytes to numbers."""
    byteCode = sampleWidthDict[sampleWidth]
    actualNumFrames = int(len(byteStr) / float(sampleWidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, byteStr)

    return audioFrameList


def convertToBytes(numList: Tuple[int, ...], sampleWidth: int) -> bytes:
    """Convert frames of a python wave object from numbers to bytes."""
    byteCode = sampleWidthDict[sampleWidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)

    return byteStr


def extractSubwav(fn: str, outputFN: str, startTime: float, endTime: float) -> None:
    """Get a subsegment of an audio file."""
    wav = QueryWav(fn)
    frames = wav.getFrames(startTime, endTime)
    wav.outputFrames(frames, outputFN)


def getDuration(fn: str) -> float:
    """Get the total duration of an audio file."""
    return QueryWav(fn).duration


def readFramesAtTime(
    audiofile: wave.Wave_read, startTime: float, endTime: float
) -> bytes:
    """Read the audio frames for the specified internal of an audio file."""
    params = audiofile.getparams()
    frameRate = params[2]

    audiofile.setpos(round(frameRate * startTime))
    frames = audiofile.readframes(round(frameRate * (endTime - startTime)))

    return frames


def readFramesAtTimes(
    audiofile: wave.Wave_read,
    keepIntervals: Optional[Iterable[Tuple[float, float]]] = None,
    deleteIntervals: Optional[Iterable[Tuple[float, float]]] = None,
    replaceFunc: Optional[Callable[[float], bytes]] = None,
) -> bytes:
    """Read an audio file into memory, with some configuration.

    Args:
        audiofile: the time to get the interval from
        keepIntervals: duration of the interval
        deleteIntervals: the maximum allowed time
        replaceFunc: is the interval before or after the targetTime?

    Returns:
        A bytestring of the loaded audio file

    Raises:
        ArgumentError: The timestamps in keepIntervals or deleteIntervals exceed the audio duration
        ArgumentError: Only one of keepIntervals and deleteIntervals can be specified
    """
    params = audiofile.getparams()
    frameRate = params[2]
    nframes = params[3]

    duration = nframes / float(frameRate)
    markedIntervals = _computeKeepDeleteIntervals(
        0.0, duration, keepIntervals, deleteIntervals
    )

    if markedIntervals[-1][1] > duration:
        raise errors.ArgumentError(
            "Timestamps in keepIntervals and deleteIntervals cannot exceed wav file duration"
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
    def __init__(self, params: wave._wave_params):
        self.params = params

        self.nchannels: int = params[0]
        self.sampleWidth: int = params[1]
        self.frameRate: int = params[2]
        self.nframes: int = params[3]
        self.comptype = params[4]
        self.compname = params[5]

        if self.nchannels != 1:
            raise errors.ArgumentError(
                "Only audio with a single channel can be loaded. "
                f"Your file has {self.nchannels} channels."
            )

    @property
    @abstractmethod
    def duration(self) -> float:  # pragma: no cover
        pass

    def getSamplesAtTime(self, start: float, step: float, reverse: bool) -> Tuple[int, ...]:
        startTime, endTime = utils.getInterval(start, step, self.duration, reverse)
        samples = self.getSamples(startTime, endTime)

        return samples

    def findNearestZeroCrossing(
        self, targetTime: float, timeStep: float = ZERO_CROSSING_TIMESTEP
    ) -> float:
        """Find the nearest zero crossing at the given time in an audio file.

        Look both before and after the timeStamp.

        Raises:
            ArgumentError: the timeStep is too small
            ZeroCrossingError: no zero crossings exist in the audio
        """
        # We'll read timeStep before the targetTime and after, then
        # continue reading in timeStep chunks left and right until
        # we find the zero crossing
        leftStartTime = targetTime - timeStep
        rightStartTime = targetTime

        samplesPerStep = timeStep * self.frameRate
        if samplesPerStep < 2:
            raise errors.ArgumentError(
                f"'timeStep' ({timeStep}) must be large enough to contain "
                f"multiple samples for audio framerate ({self.frameRate})"
            )

        # Find zero crossings
        oneSampleDuration = 2 / self.frameRate
        while True:
            if leftStartTime < 0 and rightStartTime > self.duration:
                raise errors.ZeroCrossingError()  # This should probably never happen

            samplesToRead: List[List[float]] = []
            if leftStartTime > 0:
                leftIncrement = timeStep + oneSampleDuration
                if leftStartTime - leftIncrement < 0:
                    leftStartTime = 0.0
                samplesToRead.append([leftStartTime, leftIncrement])

            if rightStartTime < self.duration:
                rightIncrement = timeStep + oneSampleDuration
                if rightStartTime + rightIncrement > self.duration:
                    rightIncrement = self.duration - rightStartTime
                samplesToRead.append([rightStartTime, rightIncrement])

            zeroCrossingsInTime: List[float] = []
            if samplesToRead:
                for startTime, increment in samplesToRead:
                    samples = self.getSamplesAtTime(startTime, increment, False)
                    zeroCrossingsInTime.extend(
                        _getZeroCrossings(samples, startTime, self.frameRate)
                    )

                if zeroCrossingsInTime:
                    return min(
                        zeroCrossingsInTime, key=lambda val: abs(targetTime - val)
                    )

            leftStartTime -= timeStep
            rightStartTime += timeStep

    @abstractmethod
    def getFrames(self, startTime: float, endTime: float) -> bytes:  # pragma: no cover
        pass

    @abstractmethod
    def getSamples(
        self, startTime: float, endTime: float
    ) -> Tuple[int, ...]:  # pragma: no cover
        pass

    def outputFrames(self, frames: bytes, outputFN: str) -> None:
        """Output frames using the same parameters as this Wav."""
        outWave = wave.open(outputFN, "w")
        outWave.setparams((
            self.nchannels,
            self.sampleWidth,
            self.frameRate,
            len(frames),
            self.comptype,
            self.compname,
        ))
        outWave.writeframes(frames)


class QueryWav(AbstractWav):
    """A class for getting information about a wave file.

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

    def getFrames(
        self, startTime: Optional[float] = None, endTime: Optional[float] = None,
    ) -> bytes:
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
    """A class for manipulating audio files.

    The wav file is represented by its wavform as a series of signed
    integers.  This can be very slow and take up lots of memory with
    large files.
    """

    def __init__(self, frames: bytes, params: wave._wave_params):
        self.frames = frames
        super(Wav, self).__init__(params)

    def __eq__(self, other):
        if not isinstance(other, Wav):
            return False

        return self.frames == other.frames

    def _getIndexAtTime(self, startTime: float) -> int:
        """Get the index in the frame list for the given time."""
        return round(startTime * self.frameRate * self.sampleWidth)

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
        return len(self.frames) / self.frameRate / self.sampleWidth

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
        outWave.setparams((
            self.nchannels,
            self.sampleWidth,
            self.frameRate,
            len(self.frames),
            self.comptype,
            self.compname,
        ))
        outWave.writeframes(self.frames)


class AudioGenerator:
    def __init__(self, sampleWidth: int, frameRate: int):
        self.sampleWidth = sampleWidth
        self.frameRate = frameRate

    @classmethod
    def fromWav(cls, wav: AbstractWav) -> "AudioGenerator":
        """Build an AudioGenerator with parameters derived from a Wav or QueryWav."""
        return AudioGenerator(wav.sampleWidth, wav.frameRate)

    def buildSineWaveGenerator(
        self, frequency: int, amplitude: Optional[float]
    ) -> Callable[[float], bytes]:
        """Return a function that takes a duration and returns a generated sine wave."""
        return partial(self.generateSineWave, frequency=frequency, amplitude=amplitude)

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


def _computeKeepDeleteIntervals(
    start: float,
    stop: float,
    keepIntervals: Optional[Iterable[Tuple[float, float]]] = None,
    deleteIntervals: Optional[Iterable[Tuple[float, float]]] = None,
) -> List[Tuple[float, float, str]]:
    """Return a list of intervals, each one labeled 'keep' or 'delete'."""
    if keepIntervals and deleteIntervals:
        raise errors.ArgumentError(
            "You cannot specify both 'keepIntervals' or 'deleteIntervals'."
        )

    elif not keepIntervals and not deleteIntervals:
        computedKeepIntervals = [(start, stop)]
        computedDeleteIntervals: List[Tuple[float, float]] = []

    elif deleteIntervals:
        deleteTimestamps = [(interval[0], interval[1]) for interval in deleteIntervals]
        computedKeepIntervals = utils.invertIntervalList(deleteTimestamps, start, stop)
        computedDeleteIntervals = deleteTimestamps

    elif keepIntervals:
        keepTimestamps = [(interval[0], interval[1]) for interval in keepIntervals]
        computedKeepIntervals = keepTimestamps
        computedDeleteIntervals = utils.invertIntervalList(keepTimestamps, start, stop)

    annotatedKeepIntervals = [
        (start, end, _KEEP) for start, end in computedKeepIntervals
    ]
    annotatedDeleteIntervals = [
        (start, end, _DELETE) for start, end in computedDeleteIntervals
    ]
    intervals = sorted(annotatedKeepIntervals + annotatedDeleteIntervals)

    return intervals
