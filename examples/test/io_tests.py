'''
Created on Jan 27, 2016

@author: tmahrt

Tests that praat files can be read in and then written out, and that the two
resulting files are the same.

This does not test that the file reader is correct.  If the file
reader is bad (e.g. truncates floating points to 1 decimal place), the
resulting data structures will look the same for both the source and
generated files.
'''

import unittest
import os
from os.path import join

from praatio import tgio
from praatio import dataio
from praatio import kgio
from praatio import audioio


def areTheSame(fn1, fn2, fileHandler=None):
    '''
    Tests that files contain the same data
    
    Usually we don't want to compare the raw text files.  There are minute
    differences in the way floating points values are.
    
    Also allows us to compare short and long-form textgrids
    '''
    if fileHandler is None:
        fileHandler = lambda fn: open(fn, "r").read()
    
    data1 = fileHandler(fn1)
    data2 = fileHandler(fn2)
    
    return data1 == data2


class IOTests(unittest.TestCase):
    """Testing input and output"""
    
    def __init__(self, *args, **kargs):
        super(IOTests, self).__init__(*args, **kargs)
        
        cwd = os.path.dirname(os.path.realpath(__file__))
        root = os.path.split(cwd)[0]
        self.dataRoot = join(root, "files")
        self.outputRoot = join(self.dataRoot, "io_test_output")
        
    def setUp(self):
        if not os.path.exists(self.outputRoot):
            os.mkdir(self.outputRoot)
    
    def test_tg_io(self):
        '''Tests for reading/writing textgrid io'''
        fn = "textgrid_to_merge.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)
        
        tg = tgio.openTextgrid(inputFN)
        tg.save(outputFN)
        
        self.assertTrue(areTheSame(inputFN, outputFN, tgio.openTextgrid))
    
    def test_tg_io_long_vs_short(self):
        '''Tests reading of long vs short textgrids'''
        
        shortFN = join(self.dataRoot, "textgrid_to_merge.TextGrid")
        longFN = join(self.dataRoot, "textgrid_to_merge_longfile.TextGrid")
        
        self.assertTrue(areTheSame(shortFN, longFN, tgio.openTextgrid))
    
    def test_get_audio_duration(self):
        '''Tests that the two audio duration methods output the same value.'''
        wavFN = join(self.dataRoot, "bobby.wav")
        
        durationA = tgio._getWavDuration(wavFN)
        durationB = audioio.getDuration(wavFN)
        self.assertTrue(durationA == durationB)
    
    def test_duration_tier_io(self):
        '''Tests for reading/writing duration tiers'''
        fn = "mary.DurationTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)
        
        dt = dataio.open2DPointObject(inputFN)
        dt.save(outputFN)
        
        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open2DPointObject))
    
    def test_pitch_io(self):
        '''Tests for reading/writing pitch tiers'''
        fn = "mary.PitchTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)
        
        pp = dataio.open2DPointObject(inputFN)
        pp.save(outputFN)
        
        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open2DPointObject))

    def test_pitch_io_long_vs_short(self):
        '''Tests reading of long vs short 2d point objects'''
        
        shortFN = join(self.dataRoot, "mary.PitchTier")
        longFN = join(self.dataRoot, "mary_longfile.PitchTier")
        
        self.assertTrue(areTheSame(shortFN, longFN, dataio.open2DPointObject))

    def test_point_process_io(self):
        '''Tests for reading/writing point processes'''
        fn = "bobby.PointProcess"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)
        
        pp = dataio.open1DPointObject(inputFN)
        pp.save(outputFN)
        
        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open1DPointObject))
        
    def test_point_process_io_long_vs_short(self):
        
        shortFN = join(self.dataRoot, "bobby.PointProcess")
        longFN = join(self.dataRoot, "bobby_longfile.PointProcess")
        
        self.assertTrue(areTheSame(shortFN, longFN, dataio.open1DPointObject))

    def test_kg_io(self):
        '''Tests for reading/writing klattgrids'''
        fn = "bobby.KlattGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)
        
        kg = kgio.openKlattGrid(inputFN)
        kg.save(outputFN)
        
        self.assertTrue(areTheSame(inputFN, outputFN, kgio.openKlattGrid))
 
 
if __name__ == "__main__":
    unittest.main()
