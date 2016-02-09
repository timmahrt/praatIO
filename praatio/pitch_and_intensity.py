# coding: utf-8
'''
Created on Oct 20, 2014

@author: tmahrt

To be used in conjunction with get_pitch_and_intensity.praat.

For brevity, 'pitch_and_intensity' is referred to as 'PI'
'''

import os
from os.path import join
import math

from praatio import tgio
from praatio.utilities import utils
from praatio.utilities import myMath


class OverwriteException(Exception):
    
    def __str__(self):
        return ("Performing this operation will result in the pitch files "
                "being overwritten.  Please change the output directory "
                "to an alternative location or add a suffix to the output. ")


def audioToPI(inputPath, inputFN, outputPath, outputFN, praatEXE,
              minPitch, maxPitch, scriptFN=None,
              sampleStep=0.01, pitchFilterWindowSize=0, forceRegenerate=True):
    '''
    Extracts pitch and intensity values from an audio file
    
    Results the result as a list.  Will load the serialized result
    if this has already been called on the appropriate files before
    
    male: minPitch=50; maxPitch=350
    female: minPitch=75; maxPitch=450
    
    mac: praatPath=/Applications/praat.App/Contents/MacOS/Praat
    windows: praatPath="C:\
    '''
    
    inputFullFN = join(inputPath, inputFN)
    outputFullFN = join(outputPath, outputFN)
    
    utils.makeDir(outputPath)
    
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath,
                        "get_pitch_and_intensity_via_python.praat")
    
    assert(os.path.exists(inputFullFN))
    firstTime = not os.path.exists(outputFullFN)
    if firstTime or forceRegenerate is True:
        
        # The praat script uses append mode, so we need to clear any prior
        # result
        if os.path.exists(outputFullFN):
            os.remove(outputFullFN)
        
        utils.runPraatScript(praatEXE, scriptFN,
                             [inputFullFN, outputFullFN, sampleStep,
                              minPitch, maxPitch])

    piList = loadPIAndTime(outputPath, outputFN)
    
    return piList


def loadPIAndTime(rawPitchDir, fn):
    '''
    For reading the output of get_pitch_and_intensity
    '''
    name = os.path.splitext(fn)[0]
    
    try:
        data = open(join(rawPitchDir, fn), "rU").read()
    except IOError:
        print("No pitch track for: %s" % name)
        raise
        
    dataList = data.splitlines()
    
    dataList = [row.split(',') for row in dataList if row != '']
    
    newDataList = []
    for time, f0Val, intensity in dataList:
        time = float(time)
        if '--' in f0Val:
            f0Val = 0.0
        else:
            f0Val = float(f0Val)
            
        if '--' in intensity:
            intensity = 0.0
        else:
            intensity = float(intensity)
        
        newDataList.append((time, f0Val, intensity))

    dataList = newDataList

    return dataList


def generatePIMeasures(dataList, tgPath, tgFN, tierName, doPitch):
    '''
    Generates processed values for the labeled intervals in a textgrid

    nullLabelList - labels to ignore in the textgrid.  Defaults to ["",]
      
    if 'doPitch'=true get pitch measures; if =false get rms intensity
    '''
    
    tgFN = join(tgPath, tgFN)
    tg = tgio.openTextGrid(tgFN)
    piData = tg.tierDict[tierName].getValuesInIntervals(dataList)
    
    outputList = []
    for interval, entryList in piData:
        label = interval[0]
        if doPitch:
            tmpValList = [f0Val for _, f0Val, _ in entryList]
            f0Measures = getPitchMeasures(tmpValList, tgFN, label,
                                          True, True)
            outputList.append(list(f0Measures))
        else:
            tmpValList = [intensityVal for _, _, intensityVal in entryList]
    
            tmpValList = [intensityVal for intensityVal in tmpValList
                          if intensityVal != 0.0]
        
            rmsIntensity = 0
            if len(tmpValList) != 0:
                rmsIntensity = myMath.rms(tmpValList)
            outputList.append([rmsIntensity, ])
    
    return outputList


def getPitchMeasures(f0Values, name=None, label=None,
                     medianFilterWindowSize=None,
                     filterZeroFlag=False,):
    '''
    Get various measures (min, max, etc) for the passed in list of pitch values
    
    name is the name of the file.  Label is the label of the current interval.
    Both of these labels are only used debugging and can be ignored if desired.
    medianFilterWindowSize: None -> no median filtering
    filterZeroFlag:True -> zero values are removed
    '''
    
    if name is None:
        name = "unspecified"
    if label is None:
        label = "unspecified"
    
    if medianFilterWindowSize is not None:
        f0Values = myMath.medianFilter(f0Values, medianFilterWindowSize,
                                       useEdgePadding=True)
        
    if filterZeroFlag:
        f0Values = [f0Val for f0Val in f0Values if int(f0Val) != 0]
    
    if len(f0Values) == 0:
        myStr = u"No pitch data for file: %s, label: %s" % (name, label)
        print(myStr.encode('ascii', 'replace'))
        counts = 0
        meanF0 = 0
        maxF0 = 0
        minF0 = 0
        rangeF0 = 0
        variance = 0
        std = 0
    else:
        counts = float(len(f0Values))
        meanF0 = sum(f0Values) / counts
        maxF0 = max(f0Values)
        minF0 = min(f0Values)
        rangeF0 = maxF0 - minF0
    
        variance = sum([(val - meanF0) ** 2 for val in f0Values]) / counts
        std = math.sqrt(variance)
            
    return (meanF0, maxF0, minF0, rangeF0, variance, std)
