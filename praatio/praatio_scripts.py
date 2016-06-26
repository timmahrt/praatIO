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


class EndOfAudioData(Exception):
    pass


class FindZeroCrossingError(Exception):
    
    def __init__(self, time, maxShiftAmount):
        super(FindZeroCrossingError, self).__init__()
        
        self.time = time
        self.maxShiftAmount = maxShiftAmount
    
    def __str__(self):
        retString = "No zero crossing found near %f with max shift amount %f"
        return retString % (self.time, self.maxShiftAmount)


def sign(x):
    retVal = 0
    if x > 0:
        retVal = 1
    elif x < 0:
        retVal = -1
    return retVal


def samplesAsNums(audiofile, numFrames, startFrame, safe=False):

    sampWidthDict = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}

    params = audiofile.getparams()
    sampwidth = params[1]
    byteCode = sampWidthDict[sampwidth]
    totalNumFrames = params[3]
    
    if safe is True:
        if totalNumFrames < startFrame + numFrames:
            numFrames = totalNumFrames - startFrame
    
    audiofile.setpos(startFrame)
    waveData = audiofile.readframes(numFrames)

    if len(waveData) == 0:
        raise EndOfAudioData()

    actualNumFrames = int(len(waveData) / float(sampwidth))
    audioFrameList = struct.unpack("<" + byteCode * actualNumFrames, waveData)

    return audioFrameList


def findNearestZeroCrossing(audiofile, timeStamp, maxShiftAmount=0.0025,
                            ignoreOnFailure=False):
    '''
    Finds the nearest zero crossing at the given time in an audio file
    
    maxShiftAmount specifies the search space (that amount before and
        after the given time)
    if ignoreOnFailure is true, a warning is printed to the screen and
        the given timestamp is returned
    '''
    framerate = audiofile.getparams()[2]
    numFrames = int(maxShiftAmount * framerate)
    
    anchorSample = int(framerate * timeStamp)
    startFrame = anchorSample - numFrames
        
    frameList = samplesAsNums(audiofile, numFrames * 2, startFrame)
    signList = [sign(val) for val in frameList]
    
    # Find zero crossings
    # 1 did signs change?
    changeList = [signList[i] != signList[i - 1]
                  for i in range(len(frameList) - 1)]
    
    # 2 get samples where signs changed
    zeroList = [i for i in range(len(frameList) - 1)
                if changeList[i] == 1]
    
    # 3 find the distance from the center point
    minDiffList = [(abs(numFrames - i), i) for i in zeroList]
    
    # 4 choose the closest sample to the center point
    try:
        smallestZeroedI = min(minDiffList)[1] - numFrames
    except ValueError:
        e = FindZeroCrossingError(timeStamp, maxShiftAmount)
        if ignoreOnFailure is not True:
            raise(e)
        else:
            print(e)
            zeroCrossingTime = timeStamp
    else:
        # 5 calculate the time that index corresponds to
        zeroCrossingSample = anchorSample + smallestZeroedI
        zeroCrossingTime = zeroCrossingSample / float(framerate)

    return zeroCrossingTime


def tgBoundariesToZeroCrossings(tgFN, wavFN, outputTGFN, adjustPoints=True,
                                maxShiftAmount=0.0025, ignoreOnFailure=False):
    '''
    Makes all textgrid interval boundaries fall on pressure wave zero crossings
    
    maxShiftAmount specifies the search space in seconds (the amount before and
        after the given time)
    if ignoreOnFailure is true, a warning is printed to the screen and
        the given timestamp is returned
    '''
    
    audiofile = wave.open(wavFN, "r")
    
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]
        
        newEntryList = []
        if isinstance(tier, tgio.PointTier) and adjustPoints is True:
            for start, label in tier.entryList:
                newStart = findNearestZeroCrossing(audiofile, start,
                                                   maxShiftAmount,
                                                   ignoreOnFailure)
                newEntryList.append((newStart, label))
                
        elif isinstance(tier, tgio.IntervalTier):
            
            for start, stop, label in tier.entryList:
                newStart = findNearestZeroCrossing(audiofile, start,
                                                   maxShiftAmount,
                                                   ignoreOnFailure)
                newStop = findNearestZeroCrossing(audiofile, stop,
                                                  maxShiftAmount,
                                                  ignoreOnFailure)
                newEntryList.append((newStart, newStop, label))
                print label, "\n"
        
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
    
    zeroBinValue = struct.pack('h', 0)
    
    # Grab the sections to be kept
    audioFrames = ""
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
               if 'label': output name is the same as label
               if None: output name plus the interval number
    '''
    tg = tgio.openTextGrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagniture = int(math.floor(math.log10(len(entryList))))
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagniture)
    
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
