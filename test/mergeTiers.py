

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
bobbyTG.addTier(praatio.TextgridTier("nouns", [entryList[1],], praatio.INTERVAL_TIER))
bobbyTG.addTier(praatio.TextgridTier("verbs", [entryList[2],], praatio.INTERVAL_TIER))
bobbyTG.addTier(praatio.TextgridTier("subjects", entryList[3:5], praatio.INTERVAL_TIER))

# Let's save it, in case you want to see it
bobbyTG.save(join(path, "mergeExample_bobby_words_split.TextGrid"))


# And we'll do the same for mary's textgrid
tg = praatio.openTextGrid(join(path, "mary.TextGrid"))
wordTier = tg.tierDict["word"]
entryList = wordTier.entryList

maryTG = praatio.Textgrid()
maryTG.addTier(tg.tierDict["phone"])
maryTG.addTier(praatio.TextgridTier("nouns", [entryList[0],], praatio.INTERVAL_TIER))
maryTG.addTier(praatio.TextgridTier("verbs", [entryList[1],], praatio.INTERVAL_TIER))
maryTG.addTier(praatio.TextgridTier("subjects", entryList[2:4], praatio.INTERVAL_TIER))

maryTG.save(join(path, "mergeExample_mary_words_split.TextGrid"))

# Let's combine Mary and Bob's textgrids
combinedTG = bobbyTG.appendTG(maryTG, True)
combinedTG.save(join(path, "mergeExample_mary_and_bob_words_split.TextGrid"))

# And now let's merge their tiers together
# We'll go with the default merge function which accepts all labels, except silence
# Any non-silent intervals that overlap will be merged together into a super interval
mergedTG = combinedTG.mergeTiers(tierList=["nouns", "verbs", "subjects"], 
                                 preserveOtherTiers=True)

mergedTG.save(join(path, "mergeExample_mary_and_bob_words_joined.TextGrid"))



