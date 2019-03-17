'''
Example of using praatio's audio splice functions
'''

import os
from os.path import join

from praatio import tgio
from praatio import audioio
from praatio import praatio_scripts

root = r"C:\Users\Tim\Dropbox\workspace\praatIO\examples\files"
audioFN = join(root, "mary.wav")
tgFN = join(root, "mary.TextGrid")

outputPath = join(root, "splice_example")
outputAudioFN = join(outputPath, "barry_spliced.wav")
outputTGFN = join(outputPath, "barry_spliced.TextGrid")

tierName = "phone"

if not os.path.exists(outputPath):
    os.mkdir(outputPath)

# Find the region to replace and the region that we'll replace it with
tg = tgio.openTextgrid(tgFN)
tier = tg.tierDict[tierName]
mEntry = tier.entryList[tier.find('m')[0]]
bEntry = tier.entryList[tier.find('b')[0]]


sourceAudioObj = audioio.openAudioFile(audioFN)
mAudioObj = sourceAudioObj.getSubsegment(mEntry[0], mEntry[1])
bAudioObj = sourceAudioObj.getSubsegment(bEntry[0], bEntry[1])

# Replace 'm' with 'b'
audioObj, tg = praatio_scripts.audioSplice(sourceAudioObj,
                                           bAudioObj,
                                           tg,
                                           tierName,
                                           "b",
                                           mEntry[0],
                                           mEntry[1])

# Replace 'b' with 'm'
# The times are now different, so we have to get them again
bEntry = tg.tierDict[tierName].entryList[tier.find('b')[0]]
audioObj, tg = praatio_scripts.audioSplice(audioObj,
                                           mAudioObj,
                                           tg,
                                           tierName,
                                           "m",
                                           bEntry[0],
                                           bEntry[1])

audioObj.save(outputAudioFN)
tg.save(outputTGFN)
