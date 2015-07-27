

from os.path import join

import praatio

path = join('.', 'files')

# Let's use praatio to construct some hypothetical textgrids
tg = praatio.openTextGrid(join(path, "bobby_words.TextGrid"))
wordTier = tg.tierDict["word"]
entryList = wordTier.entryList

bobbyPhoneTG = praatio.openTextGrid(join(path, "bobby_phones.TextGrid"))


bobbyTG = praatio.Textgrid()
bobbyTG.addTier(bobbyPhoneTG.tierDict["phone"])
bobbyTG.addTier(praatio.IntervalTier("nouns", [entryList[1],]))
bobbyTG.addTier(praatio.IntervalTier("verbs", [entryList[2],]))
bobbyTG.addTier(praatio.IntervalTier("subjects", entryList[3:5]))

# Let's save it, in case you want to see it
bobbyTG.save(join(path, "mergeExample_bobby_words_split.TextGrid"))


# And we'll do the same for mary's textgrid
tg = praatio.openTextGrid(join(path, "mary.TextGrid"))
wordTier = tg.tierDict["word"]
entryList = wordTier.entryList

maryTG = praatio.Textgrid()
maryTG.addTier(tg.tierDict["phone"])
maryTG.addTier(praatio.IntervalTier("nouns", [entryList[0],]))
maryTG.addTier(praatio.IntervalTier("verbs", [entryList[1],]))
maryTG.addTier(praatio.IntervalTier("subjects", entryList[2:4]))

maryTG.save(join(path, "mergeExample_mary_words_split.TextGrid"))

# Let's combine Mary and Bob's textgrids
combinedTG = bobbyTG.appendTextgrid(maryTG, True)
combinedTG.save(join(path, "mergeExample_mary_and_bob_words_split.TextGrid"))

# And now let's merge their tiers together
# We'll go with the default merge function which accepts all labels, 
# except silence. Any non-silent intervals that overlap will be merged
# together into a super interval
mergedTG = combinedTG.mergeTiers(tierList=["nouns", "verbs", "subjects"], 
                                 preserveOtherTiers=True)

mergedTG.save(join(path, "mergeExample_mary_and_bob_words_joined.TextGrid"))



