"""
Praatio example of correcting small differences in boundaries across different tiers.

This problem can happen when annotators are not careful
to align boundaries at the same time.
"""
import os
from os.path import join

from praatio import textgrid

path = join(".", "files")
outputPath = join(path, "aligned-tier_textgrids")

inputFN = join(path, "mary_misaligned.TextGrid")
outputFN = join(outputPath, "mary_aligned.TextGrid")
maxDifference = 0.01

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

originalTg = textgrid.openTextgrid(inputFN, False)
newTg = textgrid.Textgrid()
referenceTier = originalTg.getTier("word")
for tier in originalTg.tiers:
    if tier == referenceTier:
        newTg.addTier(tier)
        continue
    newTg.addTier(tier.dejitter(referenceTier, maxDifference))
newTg.save(outputFN, "short_textgrid", True)
