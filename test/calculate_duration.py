'''
Created on Aug 30, 2014

@author: tmahrt

Extracts the duration of each interval in each tier of the specified textgrids
and outputs the data in a csv friendly format
'''

import os
from os.path import join

import codecs

from pypraat import praatIO

path = join(".", "files")
for fn in ["bobby_phones.TextGrid", "bobby_words.TextGrid",
           "mary.TextGrid"]:
    tg = praatIO.openTextGrid(join(path, fn))
    name = os.path.splitext(fn)[0]
    
    # Get the durations for each tier
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]
        for start, stop, label in tier.entryList:
            print "%s,%s,%s,%0.2f" % (name, tierName, label, float(stop) - float(start))
    
        
    