'''
This script modifies the output of sppas, a forced-aligner tool.

It renames the textgrids, removes some tiers, renames other tiers,
and changes the contents of some tiers.

For more information on SPPAS visit the SPPAS homepage:
http://www.sppas.org/
or
https://github.com/brigittebigi/sppas

see examples/sppas_post_process.py
'''

import io
import os
from os.path import join
import shutil

from praatio import tgio
from praatio import praatio_scripts
from praatio.utilities import utils
from praatio.utilities import xsampa

# The SPPAS-produced tiers to delete
# You probably don't want to remove items from this list but you could
# add to it (for example, if a new version of SPPAS adds new tiers)
REMOVE_TIER_LIST = ["Information", "PhnTokAlign",
                    "Phonetization", "Transcription",
                    "Information-2", "MetaInformation",
                    "Activity", "Tokenization-Standard",
                    ]

# The SPPAS-produced tiers to rename
# Format: (from_name, to_name)
RENAME_TIER_LIST = [("Tokenization", "IPUs"),
                    ("TokensAlign", "words"),
                    ("PhonAlign", "phones"),
                    ]


def _decimalEqual(a, b, threshold=1e-04):
    return abs(a - b) < threshold


def _xsampaToIPATier(tg, tierName):
    
    tier = tg.tierDict[tierName]
    entryList = []
    for start, stop, label in tier.entryList:
        try:
            label = xsampa.xs2uni(label)
        except AssertionError:
            pass
        entryList.append((start, stop, label))
    
    tier = tgio.IntervalTier(tierName, entryList, 0, tg.maxTimestamp)
    tg.replaceTier(tierName, tier)
    
    return tg


def sppasPostProcess(tgPath, outputPath, removeTierList=None,
                     renameTierList=None, deleteIntermediateFiles=False):
    '''
    Cleanup SPPAS output files. Remove unused tier names.  Rename tier names.
    
    If /deleteIntermediateFiles/ is True, the xra and intermediate textgrids
    produced by SPPAS will be deleted.
    
    If /replaceOrigTextgrids/ is True, the input textgrids to SPPAS will be
    replaced by the textgrids SPPAS outputs
    '''
    
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)
    
    if removeTierList is None:
        removeTierList = REMOVE_TIER_LIST
    
    if renameTierList is None:
        renameTierList = RENAME_TIER_LIST
    
    # Remove intermediate files
    if deleteIntermediateFiles is True:
        lowerTGList = utils.findFiles(tgPath, filterExt=".textgrid")
        xraList = utils.findFiles(tgPath, ".xra")
        removeList = lowerTGList + xraList
        for fn in removeList:
            os.remove(join(tgPath, fn))
    
    # Replace the textgrids input to SPPAS (suffixed with '-merge')
    # with the textgrids that SPPAS output
    tgFNList = utils.findFiles(tgPath, filterExt=".TextGrid")
    tgFNList = [fn for fn in tgFNList
                if '-merge' in fn]
    
    # Clean up the textgrids output by SPPAS
    # Rename tiers, delete tiers, and convert the phonetic tier
    # from xsampa to IPA
    for mergeFN in tgFNList:
        
        mergeName = os.path.splitext(mergeFN)[0]
        nonMergeName = mergeName.split('-merge')[0]
        if not os.path.exists(join(outputPath, nonMergeName + ".wav")):
            shutil.copy(join(tgPath, nonMergeName + ".wav"),
                        join(outputPath, nonMergeName + ".wav"))
        if os.path.exists(join(outputPath, nonMergeName + ".TextGrid")):
            print("Skipping %s -- already exists" % mergeName + ".TextGrid")
            continue
        
        # Open tg file and remove jittered boundaries
        tg = praatio_scripts.alignBoundariesAcrossTiers(join(tgPath, mergeFN),
                                                        maxDifference=0.001)
        # Remove tiers
        for name in removeTierList:
            if name in tg.tierNameList:
                tg.removeTier(name)
        
        # Rename tiers
        for fromName, toName in renameTierList:
            if fromName in tg.tierNameList:
                tg.renameTier(fromName, toName)
        
        # Convert phones to IPA
        tg = _xsampaToIPATier(tg, "phones")
        
#         # Typically, the start and end of a spass file is silent but an
#         # utterance with only a single ipu will not acount for this.  Make
#         # a tiny amount of space for the user to be able to shift the
#         # tier if needed.
#         for tierName in tg.tierNameList:
#             tier = tg.tierDict[tierName]
#             start, stop, label = tier.entryList[0]
#             if decimalEqual(start, 0) and stop > 0.01:
#                 tier.entryList[0] = (0.01, stop, label)
#
#             start, stop, label = tier.entryList[-1]
#             duration = tg.maxTimestamp
#             if decimalEqual(stop, duration) and start < duration - 0.01:
#                 tier.entryList[-1] = (start, duration - 0.01, label)
        
        tg.save(join(outputPath, nonMergeName + ".TextGrid"))
        

def generateSingleIPUTextgrids(wavPath, txtPath, outputPath, nameMod=None,
                               addPause=True):
    '''
    Generates a textgrid with a single IPU for each wave file
    
    This constitutes the first step of SPPAS, chunking a recording into
    utterances.  In the cases when there is only a single utterance, SPPAS
    sometimes makes errors (or is not configured properly by the user).  This
    script is strictly for those situations.
    
    If there are multiple audio files for each transcript, you can derive the
    transcript name using /nameMod/
    
    If there is a chance of even a slight segment of silence on the edges of
    the audio file, /addPause/ should be True.
    '''
    if nameMod is None:
        nameMod = lambda x: x

    if not os.path.exists(outputPath):
        os.mkdir(outputPath)
    
    wavList = utils.findFiles(wavPath, filterExt=".wav", stripExt=True)
    
    for wavName in wavList:
        
        transcriptName = nameMod(wavName)
        
        # Add initial and final small pauses to each transcript
        with io.open(join(txtPath, transcriptName + ".txt"), "r") as fd:
            txt = fd.read()
            
        if addPause is True:
            txt = "+ %s +" % txt.lower()

        wavFN = join(wavPath, wavName + ".wav")
        dur = praatio_scripts.audioio.WavQueryObj(wavFN).getDuration()
        tg = tgio.Textgrid()
        tier = tgio.IntervalTier("ipu", [(0, dur, txt), ], 0, dur)
        
        tg.addTier(tier)
        tg.save(join(outputPath, wavName + ".TextGrid"))
