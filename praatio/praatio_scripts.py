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

from praatio import tgio

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


def samplesAsNums(audiofile, numFrames, startFrame):

    params = audiofile.getparams()
    sampwidth = params[1]
    byteCode = sampWidthDict[sampwidth]
    
    audiofile.setpos(startFrame)
    waveData = audiofile.readframes(numFrames)

    if len(waveData) == 0:
        raise EndOfAudioData()

    actualNumFrames = int(len(waveData) / float(sampwidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, waveData)

    return audioFrameList


def numsAsSamples(sampwidth, numList):
    
    byteCode = sampWidthDict[sampwidth]
    byteStr = struct.pack("<" + byteCode * len(numList), *numList)
    
    return byteStr
    

def findNextZeroCrossing(audiofile, targetTime, timeStep=0.002, reverse=False):
    '''
    Finds the nearest zero crossing, searching in one direction
    
    Can do a 'reverse' search by setting reverse to True.  In that case,
    the sample list is searched from back to front.
    
    targetTime is the startTime if reverse=False and
        the endTime if reverse=True
    '''
    framerate = audiofile.getparams()[2]
    totalNumFrames = audiofile.getparams()[3]
    
    startFrame = int(targetTime * float(framerate))
    numFrames = int(timeStep * float(framerate))
    
    if reverse is True:
        startFrame = startFrame - numFrames
    
    startTime = startFrame / float(framerate)
        
    # Don't read over the edges
    if startFrame < 0:
        numFrames = numFrames + startFrame
        startFrame = 0
    elif startFrame + numFrames > totalNumFrames:
        numFrames = totalNumFrames - startFrame
    
    fromTime = startFrame / float(framerate)
    toTime = (startFrame + numFrames) / float(framerate)
    
    # 1 Get the acoustic information and the sign for each sample
    frameList = samplesAsNums(audiofile, numFrames, startFrame)
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
    
    adjustTime = zeroedFrame / float(framerate)
    
    return startTime + adjustTime


def findNearestZeroCrossing(audiofile, targetTime, timeStep=0.002):
    '''
    Finds the nearest zero crossing at the given time in an audio file
    
    Looks both before and after the timeStamp
    '''
    
    framerate = audiofile.getparams()[2]
    totalNumFrames = audiofile.getparams()[3]
    fileDuration = totalNumFrames / float(framerate)
    
    leftStartTime = rightStartTime = targetTime
    
    # Find zero crossings
    smallestLeft = None
    smallestRight = None
    while True:
        try:
            timeStamp = None
            if leftStartTime > 0:
                timeStamp = findNextZeroCrossing(audiofile,
                                                 leftStartTime,
                                                 timeStep,
                                                 reverse=True)
        except FindZeroCrossingError:
            pass
        else:
            smallestLeft = timeStamp
        
        try:
            timestamp = None
            if rightStartTime < fileDuration:
                timestamp = findNextZeroCrossing(audiofile,
                                                 rightStartTime,
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


def tgBoundariesToZeroCrossings(tgFN, wavFN, outputTGFN, adjustPoints=True):
    '''
    Makes all textgrid interval boundaries fall on pressure wave zero crossings
    
    maxShiftAmount specifies the search space in seconds (the amount before and
        after the given time)
    if ignoreOnFailure is true, a warning is printed to the screen and
        the given timestamp is returned
    '''
    
    audiofile = wave.open(wavFN, "rb")
    
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]
        
        newEntryList = []
        if isinstance(tier, tgio.PointTier) and adjustPoints is True:
            for start, label in tier.entryList:
                newStart = findNearestZeroCrossing(audiofile, start)
                newEntryList.append((newStart, label))
                
        elif isinstance(tier, tgio.IntervalTier):
            
            for start, stop, label in tier.entryList:
                newStart = findNearestZeroCrossing(audiofile, start)
                newStop = findNearestZeroCrossing(audiofile, stop)
                newEntryList.append((newStart, newStop, label))
        
        tg.replaceTier(tierName, newEntryList, True)
                
    tg.save(outputTGFN)

    
def _extractSubwav(fn, outputFN, startT, endT):
    '''
    Given a segment from a wav file
    '''
    audiofile = wave.open(fn, "r")
    
    params = audiofile.getparams()
    nchannels = params[0]
    sampwidth = params[1]
    framerate = params[2]
    comptype = params[4]
    compname = params[5]

    # Extract the audio frames
    audiofile.setpos(int(framerate * startT))
    audioFrames = audiofile.readframes(int(framerate * (endT - startT)))
    
    outParams = [nchannels, sampwidth, framerate,
                 len(audioFrames), comptype, compname]
    
    outWave = wave.open(outputFN, "w")
    outWave.setparams(outParams)
    outWave.writeframes(audioFrames)
    

def deleteWavSections(fn, outputFN, deleteList, doShrink):
    '''
    Remove from the audio all of the intervals
    
    DeleteList can easily be constructed from a textgrid tier
    e.g. deleteList = tg.tierDict["targetTier"].entryList
    '''
    audiofile = wave.open(fn, "r")
    
    params = audiofile.getparams()
    nchannels = params[0]
    sampwidth = params[1]
    framerate = params[2]
    nframes = params[3]
    comptype = params[4]
    compname = params[5]

    duration = float(nframes) / framerate
    
    # Invert list (delete list -> keep list)
    deleteList = sorted(deleteList)
    
    keepList = [[deleteList[i][1], deleteList[i + 1][0]]
                for i in range(0, len(deleteList) - 1)]
    
    if len(deleteList) > 0:
        if deleteList[0][0] != 0:
            keepList.insert(0, [0, deleteList[0][0]])
            
        if deleteList[-1][1] != duration:
            keepList.append([deleteList[-1][1], duration])
    else:
        keepList.append([0, duration])
    
    keepList = [[row[0], row[1], "keep"] for row in keepList]
    deleteList = [[row[0], row[1], "delete"] for row in deleteList]
    iterList = sorted(keepList + deleteList)
    
    zeroBinValue = struct.pack(sampWidthDict[sampwidth], 0)
    
    # Grab the sections to be kept
    audioFrames = b""
    for startT, stopT, label in iterList:
        diff = stopT - startT
        
        if label == "keep":
            audiofile.setpos(int(framerate * startT))
            frames = audiofile.readframes(int(framerate * diff))
            audioFrames += frames
        
        # If we are not keeping a region and we're not shrinking the duration,
        # fill in the deleted portions with zeros
        elif label == "delete" and doShrink is False:
            frames = zeroBinValue * int(framerate * diff)
            audioFrames += frames

    # Output resulting wav file
    outParams = [nchannels, sampwidth, framerate,
                 len(audioFrames), comptype, compname]
    
    outWave = wave.open(outputFN, "w")
    outWave.setparams(outParams)
    outWave.writeframes(audioFrames)
    

def splitAudioOnTier(wavFN, tgFN, tierName, outputPath,
                     outputTGFlag=False, nameStyle=None):
    '''
    Outputs one subwav for each entry in the tier of a textgrid
    
    outputTGFlag: If True, outputs paired, cropped textgrids
                  If is type str (a tier name), outputs a paired, cropped
                  textgrid with only the specified tier
    nameStyle: if 'append': append interval label to output name
               if 'append_no_i': append label but not interval to output name
               if 'label': output name is the same as label
               if None: output name plus the interval number
    '''
    tg = tgio.openTextGrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagnitude = int(math.floor(math.log10(len(entryList))))
    
    # We want one more zero in the output than the order of magnitude
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagnitude + 1)
    
    firstWarning = True
    
    countList = [entryList.count(word) for word in entryList]
    if nameStyle == 'label':
        if sum(countList) / float(len(countList)) > 1:
            print(("Overwriting wave files in: %s\n" +
                  "Files existed before or intervals exist with the same name")
                  % outputPath)
    
    outputFNList = []
    for i, entry in enumerate(entryList):
        start, stop, label = entry
        
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
                  "Files existed before or intervals exist with the same ")
                  % outputPath)
        _extractSubwav(wavFN, outputFNFullPath, start, stop)
        outputFNList.append((start, stop, outputName + ".wav"))
        
        if outputTGFlag is not False:
            subTG = tg.crop(True, False, start, stop)
            
            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNameList:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)
        
            offset = -1 * start
            subTG = subTG.editTimestamps(offset, offset, offset)
            subTG.minTimestamp = 0
            subTG.maxTimestamp = stop - start
            
            subTG.save(join(outputPath, outputName + ".TextGrid"))
    
    return outputFNList
