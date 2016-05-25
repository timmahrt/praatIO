'''
Common/generic scripts or utilities that extend the functionality of
praatio

Created on Jul 27, 2015

@author: tmahrt
'''

import os
from os.path import join


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


def splitAudioOnTier(wavFN, tgFN, tierName, outputPath,
                     outputTGFlag=False):
    '''
    Outputs one subwav for each entry in the tier of a textgrid
    
    outputTGFlag: If True, outputs paired, cropped textgrids
                  If is type str (a tier name), outputs a paired, cropped
                  textgrid with only the specified tier
    '''
    tg = tgio.openTextGrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagniture = int(math.floor(math.log10(len(entryList))))
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagniture)
    
    outputFNList = []
    for i, entry in enumerate(entryList):
        start, stop = entry[:2]
        
        outputFN = outputTemplate % i + ".wav"
        outputFNFullPath = join(outputPath, outputFN)
        _extractSubwav(wavFN, outputFNFullPath, start, stop)
        outputFNList.append((start, stop, outputFN))
        
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
        
            subTG.save(join(outputPath, outputTemplate % i + ".TextGrid"))
    
    return outputFNList
            
