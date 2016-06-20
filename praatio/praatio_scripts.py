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


def _extractSubwav(fn, outputFN, startT, endT):
    
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
            
