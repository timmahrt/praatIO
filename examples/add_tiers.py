'''
Created on Aug 31, 2014

@author: tmahrt

Adds two tiers to the same textgrid
'''

import os
from os.path import join

from praatio import tgio

path = join('.', 'files')
outputPath = join(path, "merged_textgrids")
if not os.path.exists(outputPath):
    os.mkdir(outputPath)

tgPhones = tgio.openTextgrid(join(path, "bobby_phones.TextGrid"))
tgWords = tgio.openTextgrid(join(path, "bobby_words.TextGrid"))

tgPhones.addTier(tgWords.tierDict["word"])
tgPhones.save(join(outputPath, "bobby.TextGrid"))
