'''
Created on Aug 31, 2014

@author: tmahrt

Extracts a separate wav file for each tier in a textgrid
'''

import os
from os.path import join

from praatio import praatio_scripts

path = join(".", "files")
outputPath = join(path, "sub_wavs")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

for wavFN, tgFN in [#("bobby.wav", "bobby_words.TextGrid"),
                    ("mary.wav", "mary.TextGrid")]:
    praatio_scripts.splitAudioOnTier(join(path, wavFN),
                                     join(path, tgFN),
                                     "phone",
                                     outputPath,
                                     True)

    
    