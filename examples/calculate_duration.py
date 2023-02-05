"""
Extracts the duration of each interval in each tier of the specified textgrids

Outputs the data in a csv friendly format
"""

import os
from os.path import join

from praatio import textgrid

path = join(".", "files")
for fn in ["bobby_phones.TextGrid", "bobby_words.TextGrid", "mary.TextGrid"]:
    tg = textgrid.openTextgrid(join(path, fn), False)
    name = os.path.splitext(fn)[0]

    # Get the durations for each tier
    for tier in tg.tiers:
        if not isinstance(tier, textgrid.IntervalTier):
            continue
        for start, end, label in tier.entryList:
            txt = u"%s,%s,%s,%0.2f" % (
                name,
                tier.name,
                label,
                float(end) - float(start),
            )
            print(txt.encode("utf-8"))
