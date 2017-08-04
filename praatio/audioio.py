'''
Created on Apr 4, 2017

@author: Tim
'''

import math
import wave
import struct
import copy

from praatio.utilities import utils

sampWidthDict = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}


class EndOfAudioData(Exception):
    pass


class FindZeroCrossingError(Exception):
    
    def __init__(self, startTime, endTime):
        super(FindZeroCrossingError, self).__init__()
        
        self.startTime = startTime
        self.endTime = endTime
    
    def __str__(self):
        retString = "No zero crossing found between %f and %f"
        return retString % (self.startTime, self.endTime)


def samplesAsNums(waveData, sampleWidth):
    if len(waveData) == 0:
        raise EndOfAudioData()
    
    byteCode = sampWidthDict[sampleWidth]
    actualNumFrames = int(len(waveData) / float(sampleWidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, waveData)

    return audioFrameList


def numsAsSamples(sampleWidth, numList):
    byteCode = sampWidthDict[sampleWidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)
    
    return byteStr


def getDuration(wavFN):
    return WavQueryObj(wavFN).getDuration()

    
def getMaxAmplitude(sampleWidth):
    '''Gets the maximum possible amplitude for a given sample width'''
    return 2 ** (sampleWidth * 8 - 1) - 1


def generateSineWave(duration, freq, samplingFreq, amplitude):
    nSamples = int(duration * samplingFreq)
    wavSpec = 2 * math.pi * freq / float(samplingFreq)
    sinWave = [int(amplitude * math.sin(wavSpec * i))
               for i in range(nSamples)]
    return sinWave


def generateSilence(duration, samplingFreq):
    silence = [0, ] * int(duration * samplingFreq)
    return silence


def extractSubwav(fn, outputFN, startT, endT):
    audioObj = openAudioFile(fn, [(startT, endT), ], doShrink=True)
    audioObj.save(outputFN)
    

class AbstractWav(object):
    
    def findNearestZeroCrossing(self, targetTime, timeStep=0.002):
        '''
        Finds the nearest zero crossing at the given time in an audio file
        
        Looks both before and after the timeStamp
        '''
        
        leftStartTime = rightStartTime = targetTime
        fileDuration = self.getDuration()
        
        # Find zero crossings
        smallestLeft = None
        smallestRight = None
        while True:
            try:
                timeStamp = None
                if leftStartTime > 0:
                    timeStamp = self.findNextZeroCrossing(leftStartTime,
                                                          timeStep,
                                                          reverse=True)
            except FindZeroCrossingError:
                pass
            else:
                smallestLeft = timeStamp
            
            try:
                timestamp = None
                if rightStartTime < fileDuration:
                    timestamp = self.findNextZeroCrossing(rightStartTime,
                                                          timeStep,
                                                          reverse=False)
            except FindZeroCrossingError:
                pass
            else:
                smallestRight = timestamp
            
            if smallestLeft is not None or smallestRight is not None:
                break
            elif leftStartTime < 0 and rightStartTime > fileDuration:
                raise(FindZeroCrossingError(0, fileDuration))
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
        
        return zeroCrossingTime

    def findNextZeroCrossing(self, targetTime, timeStep=0.002,
                             reverse=False):
        '''
        Finds the nearest zero crossing, searching in one direction
        
        Can do a 'reverse' search by setting reverse to True.  In that case,
        the sample list is searched from back to front.
        
        targetTime is the startTime if reverse=False and
            the endTime if reverse=True
        '''

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
        changeList = [signList[i] != signList[i + 1]
                      for i in range(len(frameList) - 1)]
        
        # 3 get samples where signs changed
        # (iterate backwards if reverse is true)
        if reverse is True:
            start = len(changeList) - 1
            stop = 0
            step = -1
        else:
            start = 0
            stop = len(changeList) - 1
            step = 1
        
        changeIndexList = [i for i in range(start, stop, step)
                           if changeList[i] == 1]
        
        # 4 return the zeroed frame closest to starting point
        try:
            zeroedFrame = changeIndexList[0]
        except IndexError:
            raise(FindZeroCrossingError(startTime, endTime))
        
        # We found the zero by comparing points to the point adjacent to them.
        # It is possible the adjacent point is closer to zero than this one,
        # in which case, it is the better zeroedI
        if abs(frameList[zeroedFrame]) > abs(frameList[zeroedFrame + 1]):
            zeroedFrame = zeroedFrame + 1
        
        adjustTime = zeroedFrame / float(self.framerate)
        
        return startTime + adjustTime

    
class WavQueryObj(AbstractWav):
    '''
    A class for getting information about a wave file
    
    The wave file is never loaded--we only keep a reference to the
    fd.  All operations on WavQueryObj are fast.  WavQueryObjs don't
    (shouldn't) change state.  For doing multiple modifications,
    use a WavObj.
    '''
    def __init__(self, fn):
        self.audiofile = wave.open(fn, "r")
        self.params = self.audiofile.getparams()
    
        self.nchannels = self.params[0]
        self.sampwidth = self.params[1]
        self.framerate = self.params[2]
        self.nframes = self.params[3]
        self.comptype = self.params[4]
        self.compname = self.params[5]
    
    def concatenate(self, targetFrames, outputFN, prepend=False):
        sourceFrames = self.getFrames()
        
        if prepend is True:
            newFrames = targetFrames + sourceFrames
        else:
            newFrames = sourceFrames + targetFrames
        
        self.outputModifiedWav(newFrames, outputFN)
    
    def getDuration(self):
        duration = float(self.nframes) / self.framerate
        return duration
    
    def getFrames(self, startTime=None, endTime=None):
        '''
        Get frames with respect to time
        '''
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

    def getSamples(self, startTime, endTime):
        
        frames = self.getFrames(startTime, endTime)
        audioFrameList = samplesAsNums(frames, self.sampwidth)
     
        return audioFrameList

    def deleteWavSections(self, outputFN, keepList=None,
                          deleteList=None, operation="shrink",
                          sineWaveAmplitude=None):
        '''
        Remove from the audio all of the intervals
        
        DeleteList can easily be constructed from a textgrid tier
        e.g. deleteList = tg.tierDict["targetTier"].entryList
        
        operation: "shrink" to shrink the file length or "silence or
                   "sine wave" to replace the segment with silence or
                   a sine wave
        sineWaveAmplitude: if None and operation is "sine wave"
                           use max amplitude.
        '''
    
        assert(operation in ["shrink", "silence", "sine wave"])
    
        duration = float(self.nframes) / self.framerate
        
        # Need to specify what to keep or what to delete, but can't
        # specify both
        assert(keepList is not None or deleteList is not None)
        assert(keepList is None or deleteList is None)
        
        if keepList is None:
            keepList = utils.invertIntervalList(deleteList, duration)
        else:
            deleteList = utils.invertIntervalList(keepList, duration)
        keepList = [[row[0], row[1], "keep"] for row in keepList]
        deleteList = [[row[0], row[1], "delete"] for row in deleteList]
        iterList = sorted(keepList + deleteList)
        
        zeroBinValue = struct.pack(sampWidthDict[self.sampwidth], 0)
        
        # Grab the sections to be kept
        audioFrames = b""
        for startT, stopT, label in iterList:
            diff = stopT - startT
            
            if label == "keep":
                self.audiofile.setpos(int(self.framerate * startT))
                frames = self.audiofile.readframes(int(self.framerate * diff))
                audioFrames += frames
            
            # If we are not keeping a region and we're not shrinking the
            # duration, fill in the deleted portions with zeros
            elif label == "delete" and operation == "silence":
                frames = zeroBinValue * int(self.framerate * diff)
                audioFrames += frames
            # Or fill it with a sine wave
            elif label == "delete" and operation == "sine wave":
                frequency = 200
                if sineWaveAmplitude is None:
                    sineWaveAmplitude = getMaxAmplitude(self.sampwidth)
                sineWave = generateSineWave(diff,
                                            frequency,
                                            self.framerate,
                                            sineWaveAmplitude)
                frames = numsAsSamples(self.sampwidth, sineWave)
                audioFrames += frames
    
            self.outputModifiedWav(audioFrames, outputFN)
            
    def outputModifiedWav(self, audioFrames, outputFN):
        '''
        Output frames using the same parameters as this WavQueryObj
        '''
        
        # Output resulting wav file
        outParams = [self.nchannels, self.sampwidth, self.framerate,
                     len(audioFrames), self.comptype, self.compname]
        
        outWave = wave.open(outputFN, "w")
        outWave.setparams(outParams)
        outWave.writeframes(audioFrames)


class WavObj(AbstractWav):
    '''
    A class for manipulating audio files
    
    The wav file is represented by its wavform as a series of signed
    integers.  This can be very slow and take up lots of memory with
    large files.
    '''
    
    def __init__(self, audioSamples, params):

        self.audioSamples = audioSamples
        self.params = params
        self.nchannels = params[0]
        self.sampwidth = params[1]
        self.framerate = params[2]
        self.comptype = params[4]
        self.compname = params[5]
    
    def getIndexAtTime(self, startTime):
        return int(startTime * self.framerate)
    
    def insertSilence(self, startTime, silenceDuration):
        audioSamples = generateSilence(silenceDuration, self.framerate)
        self.insertSegment(startTime, audioSamples)
    
    def insert(self, startTime, valueList):
        i = self.getIndexAtTime(startTime)
        self.audioSamples = (self.audioSamples[:i] + valueList +
                             self.audioSamples[i:])
    
    def deleteSegment(self, startTime, endTime):
        i = self.getIndexAtTime(startTime)
        j = self.getIndexAtTime(endTime)
        self.audioSamples = self.audioSamples[:i] + self.audioSamples[j:]

    def getDuration(self):
        return float(len(self.audioSamples)) / self.framerate
    
    def getSamples(self, startTime, endTime):
        i = self.getIndexAtTime(startTime)
        j = self.getIndexAtTime(endTime)
        return self.audioSamples[i:j]

    def getSubsegment(self, startTime, endTime):
        samples = self.getSamples(startTime, endTime)
        return WavObj(samples, self.params)

    def new(self):
        return copy.deepcopy(self)

    def save(self, outputFN):
        # Output resulting wav file
        outParams = [self.nchannels, self.sampwidth, self.framerate,
                     len(self.audioSamples), self.comptype, self.compname]
        
        byteCode = sampWidthDict[self.sampwidth]
        byteStr = struct.pack("<" + byteCode * len(self.audioSamples),
                              *self.audioSamples)
        
        outWave = wave.open(outputFN, "w")
        outWave.setparams(outParams)
        outWave.writeframes(byteStr)


def openAudioFile(fn, keepList=None, deleteList=None, doShrink=True):
    '''
    Remove from the audio all of the intervals
    
    keepList - specifies the segments to keep; by default, everything is kept
    doShrink - if False, segments not kept are replaced by silence
    '''
    
    audiofile = wave.open(fn, "r")
    
    params = audiofile.getparams()
    sampwidth = params[1]
    framerate = params[2]
    nframes = params[3]
    
    duration = nframes / float(framerate)
    
    # Can't specify both the keepList and the deleteList
    assert(keepList is None or deleteList is None)
    
    if keepList is None and deleteList is None:
        keepList = [(0, duration), ]
        deleteList = []
    elif keepList is None:
        keepList = utils.invertIntervalList(deleteList, duration)
    else:
        deleteList = utils.invertIntervalList(keepList, duration)
        
    keepList = [[row[0], row[1], "keep"] for row in keepList]
    deleteList = [[row[0], row[1], "delete"] for row in deleteList]
    iterList = sorted(keepList + deleteList)
    
    # Grab the sections to be kept
    audioSampleList = []
    byteCode = sampWidthDict[sampwidth]
    for startT, stopT, label in iterList:
        diff = stopT - startT
        
        if label == "keep":
            audiofile.setpos(int(framerate * startT))
            frames = audiofile.readframes(int(framerate * diff))
            
            actualNumFrames = int(len(frames) / float(sampwidth))
            audioSamples = struct.unpack("<" + byteCode * actualNumFrames,
                                         frames)
            audioSampleList.extend(audioSamples)
        
        # If we are not keeping a region and we're not shrinking the
        # duration, fill in the deleted portions with zeros
        elif label == "delete" and doShrink is False:
            audioSampleList.extend([0, ] * int(framerate * diff))

    return WavObj(audioSampleList, params)
