'''
Assorted praat scripts that don't belong elsewhere exist here

These are just launchers for the actual scripts contained in praatScripts

Created on Dec 9, 2015

@author: tmahrt
'''

import os
from os.path import join

from praatio.utilities import utils


def changeGender(praatEXE, wavFN, outputWavFN, pitchFloor, pitchCeiling,
                 formantShiftRatio, pitchMedian=0.0, pitchRange=1.0,
                 duration=1.0, scriptFN=None):
    '''
    Changes the speech formants in a file using praat's change gender function

    PitchMedian = 0.0; no change in median pitch
    PitchRange = 1.0; no change in pitch range
    '''
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath,
                        "change_gender.praat")

    #  Praat crashes on exit after resynthesis with a klaatgrid
    utils.runPraatScript(praatEXE, scriptFN,
                         [wavFN, outputWavFN, pitchFloor, pitchCeiling,
                          formantShiftRatio, pitchMedian, pitchRange,
                          duration])
    

def getFormants(praatEXE, inputWavFN, outputTxtFN, maxFormant,
                stepSize=0.01, window_length=0.025, preemphasis=50,
                scriptFN=None, undefinedValue=None):
    '''
    Get F1, F2, and F3 for the audio file
    
    maxFormant = 5500 for females, 5000 for males, <8000 for children
    '''
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "get_formants.praat")

    argList = [inputWavFN, outputTxtFN, stepSize, maxFormant, window_length,
               preemphasis, -1, -1]
    utils.runPraatScript(praatEXE, scriptFN, argList)
    
    # Load the output
    path, fn = os.path.split(outputTxtFN)
    dataList = utils.openCSV(path, fn)

    # The new praat script includes a header
    if dataList[0][0] == "time":
        dataList = dataList[1:]
        
    # Handle undefined values, convert values to float
    returnList = []
    for row in dataList:
        keep = True
        for i in range(1, 4):
            if '--' in row[i]:
                if undefinedValue is not None:
                    row[i] = undefinedValue
                else:
                    keep = False
                    break
        
        if keep is True:
            returnList.append([float(val) for val in row])
    
    return returnList


def resynthesizePitch(praatEXE, inputWavFN, pitchFN, outputWavFN,
                      minPitch, maxPitch, scriptFN=None):
    '''
    Resynthesizes the pitch in a wav file with the given pitch contour
    '''
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "resynthesize_pitch.praat")

    utils.runPraatScript(praatEXE, scriptFN,
                         [inputWavFN, pitchFN, outputWavFN,
                          minPitch, maxPitch])


def resynthesizeDuration(praatEXE, inputWavFN, durationTierFN, outputWavFN,
                         minPitch, maxPitch, scriptFN=None):
    '''
    Resynthesizes the duration in a wav file with the given duration tier
    '''
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "resynthesize_duration.praat")

    utils.runPraatScript(praatEXE, scriptFN,
                         [inputWavFN, durationTierFN, outputWavFN,
                          minPitch, maxPitch])
    

def annotateSilences(praatEXE, inputWavPath, outputTGPath,
                     minPitch=100, timeStep=0.0, silenceThreshold=-25.0,
                     minSilDur=0.1, minSoundDur=0.1,
                     silentLabel='silence', soundLabel='sound', scriptFN=None):
    '''
    Marks the silences and non-silences of an audio file
    '''
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "annotate_silences.praat")

    utils.runPraatScript(praatEXE, scriptFN,
                         [inputWavPath, outputTGPath, minPitch, timeStep,
                          silenceThreshold, minSilDur, minSoundDur,
                          silentLabel, soundLabel])
