"""
Praatio example of adding two tiers to the same textgrid
"""

import os
from os.path import join

from praatio import textgrid

path = join(".", "files")
outputPath = join(path, "merged_textgrids")
if not os.path.exists(outputPath):
    os.mkdir(outputPath)

tgPhones = textgrid.openTextgrid(join(path, "bobby_phones.TextGrid"))
tgWords = textgrid.openTextgrid(join(path, "bobby_words.TextGrid"))

tgPhones.addTier(tgWords.tierDict["word"])
tgPhones.save(join(outputPath, "bobby.TextGrid"))
