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
import io

from praatio import tgio
from praatio.utilities import utils
from praatio.utilities import myMath
from praatio import praatio_scripts


class OverwriteException(Exception):
    
    def __str__(self):
        return ("Performing this operation will result in the pitch files "
                "being overwritten.  Please change the output directory "
                "to an alternative location or add a suffix to the output. ")


def _audioToPIPiecewise(inputPath, inputFN, outputPath, outputFN, praatEXE,
                        minPitch, maxPitch, tgPath, tgFN, tierName,
                        tmpOutputPath, sampleStep=0.01, silenceThreshold=0.03,
                        forceRegenerate=True, undefinedValue=None):
    '''
    Extracts pitch and int from each labeled interval in a textgrid
    
    This has the benefit of being faster than using _audioToPIFile if only
    labeled regions need to have their pitch values sampled, particularly
    for longer files.
    
    Returns the result as a list.  Will load the serialized result
    if this has already been called on the appropriate files before
    '''
    
    inputFullFN = join(inputPath, inputFN)
    tgFullFN = join(tgPath, tgFN)
    outputFullFN = join(outputPath, outputFN)
    
    utils.makeDir(outputPath)
    
    assert(os.path.exists(inputFullFN))
    firstTime = not os.path.exists(outputFullFN)
    if firstTime or forceRegenerate is True:
        
        utils.makeDir(tmpOutputPath)
        splitAudioList = praatio_scripts.splitAudioOnTier(inputFullFN,
                                                          tgFullFN,
                                                          tierName,
                                                          tmpOutputPath,
                                                          False)
        allPIList = []
        for start, _, fn in splitAudioList:
            tmpTrackName = os.path.splitext(fn)[0] + ".txt"
            piList = _audioToPIFile(tmpOutputPath, fn, tmpOutputPath,
                                    tmpTrackName, praatEXE, minPitch, maxPitch,
                                    sampleStep, silenceThreshold,
                                    forceRegenerate=True)
            piList = [("%0.3f" % (float(time) + start), str(pV), str(iV))
                      for time, pV, iV in piList]
            allPIList.extend(piList)
            
        allPIList = [",".join(row) for row in allPIList]
        with open(outputFullFN, "w") as fd:
            fd.write("\n".join(allPIList) + "\n")

    piList = loadPIAndTime(outputPath, outputFN, undefinedValue=undefinedValue)
    
    return piList


def _audioToPIFile(inputPath, inputFN, outputPath, outputFN, praatEXE,
                   minPitch, maxPitch, sampleStep=0.01, silenceThreshold=0.03,
                   forceRegenerate=True,
                   tgPath=None, tgFN=None, tierName=None, undefinedValue=None):
    '''
    Extracts pitch and intensity values from an audio file
    
    Returns the result as a list.  Will load the serialized result
    if this has already been called on the appropriate files before
    '''
    
    inputFullFN = join(inputPath, inputFN)
    outputFullFN = join(outputPath, outputFN)
    
    utils.makeDir(outputPath)
    
    assert(os.path.exists(inputFullFN))
    firstTime = not os.path.exists(outputFullFN)
    if firstTime or forceRegenerate is True:
        
        # The praat script uses append mode, so we need to clear any prior
        # result
        if os.path.exists(outputFullFN):
            os.remove(outputFullFN)
        
        if tgPath is None or tgFN is None or tierName is None:
            argList = [inputFullFN, outputFullFN, sampleStep,
                       minPitch, maxPitch, silenceThreshold, -1, -1]
            
            scriptName = "get_pitch_and_intensity_via_python.praat"
            scriptFN = join(utils.scriptsPath, scriptName)
            utils.runPraatScript(praatEXE, scriptFN, argList)
            
        else:
            argList = [inputFullFN, outputFullFN,
                       join(tgPath, tgFN), tierName, sampleStep,
                       minPitch, maxPitch, silenceThreshold]
            
            scriptName = "get_pitch_and_intensity_segments_via_python.praat"
            scriptFN = join(utils.scriptsPath, scriptName)
            utils.runPraatScript(praatEXE, scriptFN, argList)

    piList = loadPIAndTime(outputPath, outputFN, undefinedValue=undefinedValue)
    
    return piList


def audioToPI(inputPath, inputFN, outputPath, outputFN, praatEXE,
              minPitch, maxPitch, sampleStep=0.01,
              silenceThreshold=0.03, forceRegenerate=True, tgPath=None,
              tgFN=None, tierName=None, tmpOutputPath=None,
              undefinedValue=None):
    '''
    Extracts pitch and intensity from a file wholesale or piecewise

    If the parameters for a tg are passed in, this will only extract labeled
    segments in a tier of the tg.  Otherwise, pitch will be extracted from
    the entire file.

    male: minPitch=50; maxPitch=350
    female: minPitch=75; maxPitch=450
    '''
    
    if tgPath is None or tgFN is None or tierName is None:
        piList = _audioToPIFile(inputPath, inputFN, outputPath, outputFN,
                                praatEXE, minPitch, maxPitch,
                                sampleStep, silenceThreshold, forceRegenerate,
                                undefinedValue=undefinedValue)
    else:
        if tmpOutputPath is None:
            tmpOutputPath = join(outputPath, "piecewise_output")
        piList = _audioToPIPiecewise(inputPath, inputFN, outputPath, outputFN,
                                     praatEXE, minPitch, maxPitch, tgPath,
                                     tgFN, tierName, tmpOutputPath, sampleStep,
                                     silenceThreshold, forceRegenerate,
                                     undefinedValue=undefinedValue)
    
    return piList


def loadPIAndTime(rawPitchDir, fn, undefinedValue=None):
    '''
    For reading the output of get_pitch_and_intensity
    
    If undefinedValue is not None, undefined pitch or intensity values
    will be replaced with it.  Otherwise, if None, if either value is
    undefined, both are discarded.
    
    '''
    name = os.path.splitext(fn)[0]
    
    try:
        with io.open(join(rawPitchDir, fn), "r", encoding='utf-8') as fd:
            data = fd.read()
    except IOError:
        print("No pitch track for: %s" % name)
        raise
        
    dataList = data.splitlines()
    
    dataList = [row.split(',') for row in dataList if row != '']
    
    # The new praat script includes a header
    if dataList[0][0] == "time":
        dataList = dataList[1:]
    
    newDataList = []
    for time, f0Val, intensity in dataList:
        time = float(time)
        if '--' in f0Val:
            if undefinedValue is not None:
                f0Val = undefinedValue
            else:
                continue
        else:
            f0Val = float(f0Val)
            
        if '--' in intensity:
            if undefinedValue is not None:
                intensity = undefinedValue
            else:
                continue
        else:
            intensity = float(intensity)
        
        newDataList.append((time, f0Val, intensity))

    dataList = newDataList

    return dataList


def generatePIMeasures(dataList, tgPath, tgFN, tierName, doPitch,
                       medianFilterWindowSize=None):
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
                                          medianFilterWindowSize, True)
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


def detectPitchErrors(pitchList, maxJumpThreshold=0.70, tgToMark=None):
    '''
    Detect pitch halving and doubling errors.
    
    If a textgrid is passed in, it adds the markings to the textgrid
    '''
    assert(maxJumpThreshold >= 0.0 and maxJumpThreshold <= 1.0)
    
    errorList = []
    for i in range(1, len(pitchList)):
        lastPitch = pitchList[i - 1][1]
        currentPitch = pitchList[i][1]
        
        ceilingCutoff = currentPitch / maxJumpThreshold
        floorCutoff = currentPitch * maxJumpThreshold
        if((lastPitch <= floorCutoff) or (lastPitch >= ceilingCutoff)):
            currentTime = pitchList[i][0]
            errorList.append([currentTime, currentPitch / lastPitch])
    
    if tgToMark is not None:
        tierName = "pitch errors"
        assert(tierName not in tgToMark.tierNameList)
        pointTier = tgio.PointTier(tierName, errorList,
                                   tgToMark.minTimestamp,
                                   tgToMark.maxTimestamp)
        tgToMark.addTier(pointTier)
    
    return errorList, tgToMark
