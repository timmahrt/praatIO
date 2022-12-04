#!/usr/bin/env python
# encoding: utf-8
"""
Created on Oct 21, 2021

@author: tmahrt
"""

import os
from os.path import join

from praatio import audio

path = join(".", "files")
outputPath = join(path, "sub_wavs")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

inputFN = join(path, "mary.wav")
outputFN = join(outputPath, "mary_segment.wav")
audio.extractSubwav(inputFN, outputFN, 0.33, 0.89)
