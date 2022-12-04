"""
Replaces someone saying a name with a tone over the name to 'hide' the name.

The times that the names are spoken are taken from a transcript
of the recording.
"""

import os
from os.path import join

from praatio import textgrid
from praatio import audio

path = join(".", "files")
outputPath = join(path, "anonymized_data")

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

for wavFN, tgFN in (
    ("mary.wav", "mary.TextGrid"),
    ("bobby.wav", "bobby_words.TextGrid"),
):

    outputWavFN = join(outputPath, wavFN)

    # Find the word(s) to anonymize
    # (One could imagine a search for common names or identification of
    # some sort of code ('section-to-anonymize') rather than what I have
    # done here.
    deleteList = []
    tg = textgrid.openTextgrid(join(path, tgFN), False)
    deleteList.append(tg.tierDict["word"].entryList[0])

    # Get only time information from entries (i.e. remove label information)
    deleteList = [(start, end) for start, end, _ in deleteList]

    # Replace segments with a sine wave
    wav = audio.Wav.open(join(path, wavFN))
    for start, end in deleteList:
        sineFrames = audio.AudioGenerator(
            wav.sampleWidth, wav.frameRate
        ).generateSineWave(end - start, audio.DEFAULT_SINE_FREQUENCY)
        wav.replaceSegment(start, end, sineFrames)
