"""
Praatio example of correcting small differences in boundaries across different tiers

This problem can happen when annotators are not careful
to align boundaries at the same time.
"""

import os
from os.path import join

from praatio import textgrid
from praatio import praatio_scripts

path = join(".", "files")
outputPath = join(path, "aligned-tier_textgrids")

inputFN = join(path, "mary_misaligned.TextGrid")
outputFN = join(outputPath, "mary_aligned.TextGrid")
maxDifference = 0.01

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

originalTg = textgrid.openTextgrid(inputFN, False)
tg = praatio_scripts.alignBoundariesAcrossTiers(originalTg, "word", maxDifference)
tg.save(outputFN, "short_textgrid", True)
