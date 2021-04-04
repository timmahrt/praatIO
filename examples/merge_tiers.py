"""
Example of using praatio for merging tiers together.
"""

import os
from os.path import join

from praatio import tgio


path = join(".", "files")
outputPath = join(path, "merged_textgrids")
if not os.path.exists(outputPath):
    os.mkdir(outputPath)

# Let's use praatio to construct some hypothetical textgrids
tg = tgio.openTextgrid(join(path, "bobby_words.TextGrid"))
wordTier = tg.tierDict["word"]
entryList = wordTier.entryList

bobbyPhoneTG = tgio.openTextgrid(join(path, "bobby_phones.TextGrid"))


bobbyTG = tgio.Textgrid()
bobbyTG.addTier(bobbyPhoneTG.tierDict["phone"])
bobbyTG.addTier(
    tgio.IntervalTier(
        "nouns",
        [
            entryList[1],
        ],
    )
)
bobbyTG.addTier(
    tgio.IntervalTier(
        "verbs",
        [
            entryList[2],
        ],
    )
)
bobbyTG.addTier(tgio.IntervalTier("subjects", entryList[3:5]))

# Let's save it, in case you want to see it
bobbyTG.save(join(outputPath, "mergeExample_bobby_words_split.TextGrid"))


# And we'll do the same for mary's textgrid
tg = tgio.openTextgrid(join(path, "mary.TextGrid"))
wordTier = tg.tierDict["word"]
entryList = wordTier.entryList

maryTG = tgio.Textgrid()
maryTG.addTier(tg.tierDict["phone"])
maryTG.addTier(
    tgio.IntervalTier(
        "nouns",
        [
            entryList[0],
        ],
    )
)
maryTG.addTier(
    tgio.IntervalTier(
        "verbs",
        [
            entryList[1],
        ],
    )
)
maryTG.addTier(tgio.IntervalTier("subjects", entryList[2:4]))

maryTG.save(join(outputPath, "mergeExample_mary_words_split.TextGrid"))

# Let's combine Mary and Bob's textgrids
combinedTG = bobbyTG.appendTextgrid(maryTG, True)
combinedTG.save(join(outputPath, "mergeExample_mary_and_bob_words_split.TextGrid"))

# And now let's merge their tiers together
# We'll go with the default merge function which accepts all labels,
# except silence. Any non-silent intervals that overlap will be merged
# together into a super interval
mergedTG = combinedTG.mergeTiers(
    tierList=["nouns", "verbs", "subjects"], preserveOtherTiers=True
)

mergedTG.save(join(outputPath, "mergeExample_mary_and_bob_words_joined.TextGrid"))
