'''
Created on Aug 31, 2014

@author: tmahrt

Extracts a separate wav file for each tier in a textgrid
'''

import os
from os.path import join

import wave
import audioop

from pypraat import praatIO


def extractSubwav(fn, outputFN, startT, endT, singleChannelFlag):
    
    audiofile = wave.open(fn, "r")
    
    params = audiofile.getparams()
    nchannels, sampwidth, framerate, nframes, comptype, compname = params

    # Extract the audio frames
    audiofile.setpos(int(framerate*startT))
    audioFrames = audiofile.readframes(int(framerate*(endT - startT)))
    
    # Convert to single channel if needed
    if singleChannelFlag == True and nchannels > 1:
        audioFrames = audioop.tomono(audioFrames, sampwidth, 1, 0)
        nchannels = 1
    
    outParams = [nchannels, sampwidth, framerate, len(audioFrames), comptype, compname]
    
    outWave = wave.open(outputFN, "w")
    outWave.setparams(outParams)
    outWave.writeframes(audioFrames)


path = join(".", "files")
outputPath = join(path, "sub_wavs")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

for wavFN, tgFN in [("bobby.wav", "bobby_words.TextGrid"),
                    ("mary.wav", "mary.TextGrid")]:
    print tgFN
    fullPath = join(path, tgFN)
    tg = praatIO.openTextGrid(fullPath)
    tier = tg.tierDict["word"]
    name = os.path.splitext(wavFN)[0]
    for i, intervalList in enumerate(tier.entryList):
        start, stop, label = intervalList
        extractSubwav(join(path, wavFN), 
                      join(outputPath, "%s_%03d_%s.wav" % (name, i, label)),
                      start, stop, True)
    
    