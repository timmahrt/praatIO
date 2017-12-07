'''
Created on Dec 7, 2017

@author: Tim
'''

import unittest
import os
from os.path import join

from praatio import tgio
from praatio import dataio
from praatio import kgio
from praatio import audioio

class IOTests(unittest.TestCase):
    """Testing input and output"""
    
    def __init__(self, *args, **kargs):
        super(IOTests, self).__init__(*args, **kargs)
        
        cwd = os.path.dirname(os.path.realpath(__file__))
        root = os.path.split(cwd)[0]
        self.dataRoot = join(root, "files")
        self.outputRoot = join(self.dataRoot, "io_test_output")
    
    def test_shift(self):
        '''Testing adjustments to textgrid times'''
        tgFN = join(self.dataRoot, "mary.TextGrid")
        
        tg = tgio.openTextgrid(tgFN)
        shiftedTG = tg.editTimestamps(0.1, True)
        unshiftedTG = shiftedTG.editTimestamps(-0.1, True)
    
        self.assertTrue(tg == unshiftedTG)
    
    def test_insert_delete_space(self):
        '''Testing insertion and deletion of space in a textgrid'''
        tgFN = join(self.dataRoot, "mary.TextGrid")
        
        tg = tgio.openTextgrid(tgFN)
        stretchedTG = tg.insertSpace(1, 1, 'stretch')
        unstretchedTG = stretchedTG.eraseRegion(1, 2, doShrink=True)
        
        self.assertTrue(tg == unstretchedTG)
    
    def test_rename_tier(self):
        '''Testing renaming of tiers'''
        
        tgFN = join(self.dataRoot, "mary.TextGrid")
        
        tg = tgio.openTextgrid(tgFN)
        
        tg.renameTier("phone", "candy")
        
        self.assertTrue("phone" not in tg.tierNameList)
        self.assertTrue("candy" in tg.tierNameList)
    
    def setUp(self):
        if not os.path.exists(self.outputRoot):
            os.mkdir(self.outputRoot)

if __name__ == "__main__":
    unittest.main()