'''
Common/generic scripts or utilities that extend the functionality of
praatio

Created on Jul 27, 2015

@author: tmahrt
'''

import os
from os.path import join

import struct
import math
import wave
import copy

from praatio import tgio
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


def sign(x):
    retVal = 0
    if x > 0:
        retVal = 1
    elif x < 0:
        retVal = -1
    return retVal


def samplesAsNums(waveData, sampwidth):
    byteCode = sampWidthDict[sampwidth]
    actualNumFrames = int(len(waveData) / float(sampwidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, waveData)

    return audioFrameList


def numsAsSamples(sampwidth, numList):
    
    byteCode = sampWidthDict[sampwidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)
    
    return byteStr


def tgBoundariesToZeroCrossings(tgFN, wavFN, outputTGFN, adjustPoints=True):
    '''
    Makes all textgrid interval boundaries fall on pressure wave zero crossings
    
    maxShiftAmount specifies the search space in seconds (the amount before and
        after the given time)
    if ignoreOnFailure is true, a warning is printed to the screen and
        the given timestamp is returned
    '''
    
    wavQObj = WavQueryObj(wavFN)
    
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]
        
        newEntryList = []
        if isinstance(tier, tgio.PointTier) and adjustPoints is True:
            for start, label in tier.entryList:
                newStart = wavQObj.findNearestZeroCrossing(start)
                newEntryList.append((newStart, label))
                
        elif isinstance(tier, tgio.IntervalTier):
            
            for start, stop, label in tier.entryList:
                newStart = wavQObj.findNearestZeroCrossing(start)
                newStop = wavQObj.findNearestZeroCrossing(stop)
                newEntryList.append((newStart, newStop, label))
        
        tg.replaceTier(tierName, newEntryList, True)
                
    tg.save(outputTGFN)

    
def _extractSubwav(fn, outputFN, startT, endT):
    '''
    Given a segment from a wav file
    '''
    audioObj = openAudioFile(fn, [(startT, endT), ], True)
    audioObj.save(outputFN)


class WavQueryObj(object):
    '''
    A class for getting information about a wave file
    
    The wave file is never loaded--we only keep a reference to the
    fd.
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
    
    def getDuration(self):
        duration = float(self.nframes) / self.framerate
        return duration
    
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
        
        startFrame = int(targetTime * float(self.framerate))
        numFrames = int(timeStep * float(self.framerate))
        
        if reverse is True:
            startFrame = startFrame - numFrames
        
        startTime = startFrame / float(self.framerate)
            
        # Don't read over the edges
        if startFrame < 0:
            numFrames = numFrames + startFrame
            startFrame = 0
        elif startFrame + numFrames > self.nframes:
            numFrames = self.nframes - startFrame
        
        fromTime = startFrame / float(self.framerate)
        toTime = (startFrame + numFrames) / float(self.framerate)
        
        # 1 Get the acoustic information and the sign for each sample
        frameList = self.samplesAsNums(numFrames, startFrame)
        signList = [sign(val) for val in frameList]
        
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
            raise(FindZeroCrossingError(fromTime, toTime))
        
        # We found the zero by comparing points to the point adjacent to them.
        # It is possible the adjacent point is closer to zero than this one,
        # in which case, it is the better zeroedI
        if abs(frameList[zeroedFrame]) > abs(frameList[zeroedFrame + 1]):
            zeroedFrame = zeroedFrame + 1
        
        adjustTime = zeroedFrame / float(self.framerate)
        
        return startTime + adjustTime
    
    def samplesAsNums(self, startTime, duration):
        startFrame = int(startTime * float(self.framerate))
        numFrames = int(duration * float(self.framerate))
        self.audiofile.setpos(startFrame)
        waveData = self.audiofile.readframes(numFrames)
        
        if len(waveData) == 0:
            raise EndOfAudioData()
     
        audioFrameList = samplesAsNums(waveData, self.sampwidth)
     
        return audioFrameList


class WavObj(object):
    '''
    A class for manipulating audio files
    
    The wav file is represented by its wavform as a series of signed
    integers.
    '''
    
    def __init__(self, frameList, params):

        self.frameList = frameList
        self.params = params
        self.nchannels = params[0]
        self.sampwidth = params[1]
        self.framerate = params[2]
        self.comptype = params[4]
        self.compname = params[5]
    
    def getIndexAtTime(self, startTime):
        return int(startTime * self.framerate)
    
    def insertSilence(self, startTime, silenceDuration):
        i = self.getIndexAtTime(startTime)
        frames = [0, ] * int(self.framerate * silenceDuration)
        self.frameList = self.frameList[:i] + frames + self.frameList[i:]
    
    def getDuration(self):
        return len(self.frameList) / self.framerate
    
    def save(self, outputFN):
        # Output resulting wav file
        outParams = [self.nchannels, self.sampwidth, self.framerate,
                     len(self.frameList), self.comptype, self.compname]
        
        byteCode = sampWidthDict[self.sampwidth]
        byteStr = struct.pack("<" + byteCode * len(self.frameList),
                              *self.frameList)
        
        outWave = wave.open(outputFN, "w")
        outWave.setparams(outParams)
        outWave.writeframes(byteStr)


def openAudioFile(fn, keepList=None, doShrink=True):
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
    
    if keepList is None:
        keepList = [(0, duration), ]
        deleteList = []
    else:
        deleteList = utils.invertIntervalList(keepList, duration)
        
    keepList = [[row[0], row[1], "keep"] for row in keepList]
    deleteList = [[row[0], row[1], "delete"] for row in deleteList]
    iterList = sorted(keepList + deleteList)
    
    # Grab the sections to be kept
    audioFrames = []
    byteCode = sampWidthDict[sampwidth]
    for startT, stopT, label in iterList:
        diff = stopT - startT
        
        if label == "keep":
            audiofile.setpos(int(framerate * startT))
            frames = audiofile.readframes(int(framerate * diff))
            
            actualNumFrames = int(len(frames) / float(sampwidth))
            audioFrameList = struct.unpack("<" + byteCode * actualNumFrames,
                                           frames)
            audioFrames.extend(audioFrameList)
        
        # If we are not keeping a region and we're not shrinking the
        # duration, fill in the deleted portions with zeros
        elif label == "delete" and doShrink is False:
            audioFrames.extend([0, ] * int(framerate * diff))

    return WavObj(audioFrames, params)


def splitAudioOnTier(wavFN, tgFN, tierName, outputPath,
                     outputTGFlag=False, nameStyle=None,
                     noPartialIntervals=False):
    '''
    Outputs one subwav for each entry in the tier of a textgrid
    
    outputTGFlag: If True, outputs paired, cropped textgrids
                  If is type str (a tier name), outputs a paired, cropped
                  textgrid with only the specified tier
    nameStyle: if 'append': append interval label to output name
               if 'append_no_i': append label but not interval to output name
               if 'label': output name is the same as label
               if None: output name plus the interval number
    noPartialIntervals: if True: intervals in non-target tiers that are
                                  not wholly contained by an interval in
                                  the target tier will not be included in
                                  the output textgrids
    '''
    tg = tgio.openTextGrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagnitude = int(math.floor(math.log10(len(entryList))))
    
    # We want one more zero in the output than the order of magnitude
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagnitude + 1)
    
    firstWarning = True
    
    # If we're using the 'label' namestyle for outputs, all of the
    # interval labels have to be unique, or wave files with those
    # labels as names, will be overwritten
    if nameStyle == 'label':
        wordList = [word for _, _, word in entryList]
        multipleInstList = []
        for word in set(wordList):
            if wordList.count(word) > 1:
                multipleInstList.append(word)
        
        if len(multipleInstList) > 0:
            instListTxt = "\n".join(multipleInstList)
            print(("Overwriting wave files in: %s\n" +
                  "Intervals exist with the same name:\n%s")
                  % (outputPath, instListTxt))
            firstWarning = False
    
    # Output wave files
    outputFNList = []
    for i, entry in enumerate(entryList):
        start, stop, label = entry
        
        # Resolve output name
        outputName = outputTemplate % i
        if nameStyle == "append":
            outputName += "_" + label
        elif nameStyle == "append_no_i":
            outputName = name + "_" + label
        elif nameStyle == "label":
            outputName = label
        
        outputFNFullPath = join(outputPath, outputName + ".wav")

        if os.path.exists(outputFNFullPath) and firstWarning:
            print(("Overwriting wave files in: %s\n" +
                   "Files existed before or intervals exist with " +
                   "the same name:\n%s")
                  % (outputPath, outputName))
        
        audioObj = openAudioFile(wavFN, [(start, stop), ], True)
        audioObj.save(outputFNFullPath)
        outputFNList.append((start, stop, outputName + ".wav"))
        
        # Output the textgrid if requested
        if outputTGFlag is not False:
            subTG = tg.crop(noPartialIntervals, False, start, stop)
            
            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNameList:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)
        
            # Adjust the new time on the intervals, the textgrid,
            # and the textgrid tiers
            # the crop start time becomes the new '0' value
            offset = -1 * start
            subTG = subTG.editTimestamps(offset, offset, offset)
            subTG.minTimestamp = 0
            subTG.maxTimestamp = stop - start
            for tierName in subTG.tierNameList:
                subTG.tierDict[tierName].minTimestamp = 0
                subTG.tierDict[tierName].maxTimestamp = stop - start
            
            subTG.save(join(outputPath, outputName + ".TextGrid"))
    
    return outputFNList


def alignBoundariesAcrossTiers(tgFN, maxDifference=0.01):
    '''
    Aligns boundaries or points in a textgrid that suffer from 'jitter'
    
    Often times, boundaries in different tiers are meant to line up.
    For example the boundary of the first phone in a word and the start
    of the word.  If manually annotated, however, those values might
    not be the same, even if they were intended to be the same.
    
    This script will force all boundaries within /maxDifference/ amount
    to be the same value.
    '''
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList:
        altNameList = [tmpName for tmpName in tg.tierNameList
                       if tmpName != tierName]
        
        tier = tg.tierDict[tierName]
        for entry in tier.entryList:
            # Interval tier left boundary or point tier point
            _findMisalignments(tg, entry[0], maxDifference,
                               altNameList, tierName, entry, 0)
            
            # Interval tier right boundary
            if tier.tierType == tgio.INTERVAL_TIER:
                _findMisalignments(tg, entry[1], maxDifference,
                                   altNameList, tierName, entry, 1)

    return tg

            
def _findMisalignments(tg, timeV, maxDifference, tierNameList,
                       tierName, entry, orderID):
    
    # Get the start time
    filterStartT = timeV - maxDifference
    if filterStartT < 0:
        filterStartT = 0
    
    # Get the end time
    filterStopT = timeV + maxDifference
    if filterStopT > tg.maxTimestamp:
        filterStopT = tg.maxTimestamp

    croppedTG = tg.crop(False, True, filterStartT, filterStopT)

    matchList = [(tierName, timeV, entry, orderID)]
    for subTierName in tierNameList:
        subCroppedTier = croppedTG.tierDict[subTierName]
        
        # For each item that exists in the search span, find the boundary
        # that lies in the search span
        for subCroppedEntry in subCroppedTier.entryList:
            
            if subCroppedTier.tierType == tgio.INTERVAL_TIER:
                subStart, subEnd, _ = subCroppedEntry
                
                # Left boundary?
                leftMatchVal = None
                if subStart >= filterStartT and subStart <= filterStopT:
                    leftMatchVal = subStart

                # Right boundary?
                rightMatchVal = None
                if subEnd >= filterStartT and subEnd <= filterStopT:
                    rightMatchVal = subEnd
                    
                # There should be at most one matching boundary
                assert(leftMatchVal is None or rightMatchVal is None)
                
                # Set the matching boundary info
                if leftMatchVal is not None:
                    matchVal = leftMatchVal
                    subOrderID = 0
                else:
                    matchVal = rightMatchVal
                    subOrderID = 1
            
                # Match value could be none if, for an interval tier,
                # no boundary sits inside the search span (the search span
                # is wholly inside the interval)
                if matchVal is None:
                    continue
            
            elif subCroppedTier.tierType == tgio.POINT_TIER:
                subStart, _ = subCroppedEntry
                if subStart >= filterStartT and subStart <= filterStopT:
                    matchVal = subStart
                    subOrderID = 0

            matchList.append((subTierName, matchVal, subCroppedEntry,
                              subOrderID))
    
    # Find the number of different values that are almost the same
    valList = [row[1] for row in matchList]
    valUniqueList = []
    for val in valList:
        if val not in valUniqueList:
            valUniqueList.append(val)
            
    # If they're all the same, there is nothing to do
    # If some are different, take the most common value (or else the first
    # one) and set all similar times to that value
    if len(valUniqueList) > 1:
        countList = [valList.count(val) for val in valUniqueList]
        bestVal = valUniqueList[countList.index(max(countList))]
        assert(bestVal is not None)
        for tierName, _, oldEntry, orderID in matchList:

            newEntry = list(copy.deepcopy(oldEntry))
            newEntry[orderID] = bestVal
            newEntry = tuple(newEntry)
        
            tg.tierDict[tierName].deleteEntry(oldEntry)
            tg.tierDict[tierName].entryList.append(newEntry)
            tg.tierDict[tierName].entryList.sort()
