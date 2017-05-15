'''
Created on Mar 27, 2016

@author: Tim

The following example is derived from real code.  It was the reason the set
operations were added to the praatio library.

The original code.  Suppose you have two tiers and want to use one tier to
filter the results of another tier.  In my case, I had textgrids with
stressed syllable and stressed vowels marked.  I wanted to extract pitch
information using this tier.  But the pitch contour contained some pitch
doubling and halving--afflicted areas were marked on a separate tier.

By taking the difference between the two tiers, we get the relevant regions,
minus areas affected by pitch halving and doubling.

I've added union and intersection here just to show their effect.
'''

import os
from os.path import join

from praatio import tgio


def doSetOperations(fromFN, toFN):
    
    tg = tgio.openTextgrid(fromFN)
    
    syllableTier = tg.tierDict['tonicSyllable']
    phoneTier = tg.tierDict['tonicVowel']
    filterTier = tg.tierDict['manually_labeled_pitch_errors']

    # Intersection
    phoneTier1 = phoneTier.intersection(filterTier)
    phoneTier1.name = 'vowel_intersection'
    syllableTier1 = syllableTier.intersection(filterTier)
    syllableTier1.name = 'syllable_intersection'
        
    tg.addTier(phoneTier1)
    tg.addTier(syllableTier1)
    
    # Difference
    phoneTier2 = phoneTier.difference(filterTier)
    phoneTier2.name = 'vowel_difference'
    syllableTier2 = syllableTier.difference(filterTier)
    syllableTier2.name = 'syllable_difference'

    tg.addTier(phoneTier2)
    tg.addTier(syllableTier2)

    # Union
    phoneTier3 = phoneTier.union(filterTier)
    phoneTier3.name = 'vowel_union'
    syllableTier3 = syllableTier.union(filterTier)
    syllableTier3.name = 'syllable_union'

    tg.addTier(phoneTier3)
    tg.addTier(syllableTier3)
        
    tg.save(toFN)


path = join(".", "files")

fromFN = join(path, "damon_set_test.TextGrid")
toPath = join(path, "set_output")
toFN = join(toPath, "damon_set_test.TextGrid")

if not os.path.exists(toPath):
    os.mkdir(toPath)

doSetOperations(fromFN, toFN)
