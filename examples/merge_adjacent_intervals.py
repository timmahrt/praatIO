"""
Example of using praatio for merging intervals that share a border.
"""

import os
from os.path import join

from praatio import textgrid


def merge_adjacent(path, fn, outputPath):
    """
    Go through every tier of a textgrid; combine adjacent filled intervals.
    """

    assert path != outputPath

    if not os.path.exists(outputPath):
        os.mkdir(outputPath)

    outputTG = textgrid.Textgrid()

    tg = textgrid.openTextgrid(join(path, fn), False)
    for tier in tg.tiers:
        newEntries = []
        currentEntry = list(tier.entries[0])
        for nextEntry in tier.entries[1:]:

            # Is a boundary shared?
            if currentEntry[1] == nextEntry[0]:
                currentEntry[1] = nextEntry[1]  # Old end = new end
                currentEntry[2] += " - " + nextEntry[2]
            # If not
            else:
                newEntries.append(currentEntry)
                currentEntry = list(nextEntry)

        newEntries.append(currentEntry)

        replacementTier = textgrid.IntervalTier(
            tier.name, newEntries, tier.minTimestamp, tier.maxTimestamp
        )
        outputTG.addTier(replacementTier)

    outputTG.save(join(outputPath, fn), "short_textgrid", True)


def merge_adjacent_batch(inputPath, outputPath):
    for fn in os.listdir(inputPath):
        if ".TextGrid" in fn:
            merge_adjacent(inputPath, fn, outputPath)


path = join(".", "files")
outputPath = join(path, "merged_textgrids")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

merge_adjacent(path, "textgrid_to_merge.TextGrid", outputPath)
