"""
Example of using praatio for merging intervals that share a border.
"""

import os
from os.path import join

from praatio import textgrid


def merge_adjacent(path, fn, outputPath):
    """
    Goes through every tier of a textgrid; combines adjacent filled intervals
    """

    assert path != outputPath

    if not os.path.exists(outputPath):
        os.mkdir(outputPath)

    outputTG = textgrid.Textgrid()

    tg = textgrid.openTextgrid(join(path, fn), False)
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]

        newEntryList = []
        currentEntry = list(tier.entryList[0])
        for nextEntry in tier.entryList[1:]:

            # Is a boundary shared?
            if currentEntry[1] == nextEntry[0]:
                currentEntry[1] = nextEntry[1]  # Old end = new end
                currentEntry[2] += " - " + nextEntry[2]
            # If not
            else:
                newEntryList.append(currentEntry)
                currentEntry = list(nextEntry)

        newEntryList.append(currentEntry)

        replacementTier = textgrid.IntervalTier(
            tierName, newEntryList, tier.minTimestamp, tier.maxTimestamp
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
