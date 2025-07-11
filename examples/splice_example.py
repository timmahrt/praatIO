"""
Example of using praatio's audio splice functions.
"""

import os
from os.path import join

from praatio import textgrid
from praatio import audio
from praatio import praatio_scripts

root = os.path.abspath(join(".", "files"))
audioFN = join(root, "mary.wav")
tgFN = join(root, "mary.TextGrid")

outputPath = join(root, "splice_example")
outputAudioFN = join(outputPath, "barry_spliced.wav")
outputTGFN = join(outputPath, "barry_spliced.TextGrid")

tierName = "phone"

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

# Find the region to replace and the region that we'll replace it with
tg = textgrid.openTextgrid(tgFN, False)
tier = tg.getTier(tierName)
mEntry = tier.entries[tier.find("m")[0]]
bEntry = tier.entries[tier.find("b")[0]]


sourceAudioObj = audio.Wav.open(audioFN)
mAudioObj = sourceAudioObj.getSubwav(mEntry[0], mEntry[1])
bAudioObj = sourceAudioObj.getSubwav(bEntry[0], bEntry[1])

# Replace 'm' with 'b'
audioObj, tg = praatio_scripts.audioSplice(
    sourceAudioObj, bAudioObj, tg, tierName, "b", mEntry[0], mEntry[1]
)

# Replace 'b' with 'm'
# The times are now different, so we have to get them again
bEntry = tg.getTier(tierName).entries[tier.find("b")[0]]
audioObj, tg = praatio_scripts.audioSplice(
    audioObj, mAudioObj, tg, tierName, "m", bEntry[0], bEntry[1]
)

audioObj.save(outputAudioFN)
tg.save(outputTGFN, "short_textgrid", True)
