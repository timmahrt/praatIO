'''
Assorted praat scripts that don't belong elsewhere exist here

These are just launchers for the actual scripts contained in praatScripts

Created on Dec 9, 2015

@author: tmahrt
'''

from os.path import join

from praatio import common


def changeGender(praatEXE, wavFN, outputWavFN, pitchFloor, pitchCeiling,
                 formantShiftRatio, pitchMedian=0.0, pitchRange=1.0,
                 duration=1.0, scriptFN=None):
    
    if scriptFN is None:
        scriptFN = join(common.scriptsPath,
                        "change_gender.praat")
    
    #  Praat crashes on exit after resynthesis with a klaatgrid
    common.runPraatScript(praatEXE, scriptFN,
                          [wavFN, outputWavFN, pitchFloor, pitchCeiling,
                           formantShiftRatio, pitchMedian, pitchRange,
                           duration],
                          exitOnError=False)
