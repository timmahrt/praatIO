'''
Assorted praat scripts that don't belong elsewhere exist here

These are just launchers for the actual scripts contained in praatScripts

Created on Dec 9, 2015

@author: tmahrt
'''

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
                          duration],
                         exitOnError=False)


