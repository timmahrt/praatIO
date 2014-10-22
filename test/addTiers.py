'''
Created on Aug 31, 2014

@author: tmahrt

Adds two tiers to the same textgrid
'''

from os.path import join

from pypraat import praatIO

path = join('.', "files")

tgPhones = praatIO.openTextGrid(join(path, "bobby_phones.TextGrid"))
tgWords = praatIO.openTextGrid(join(path, "bobby_words.TextGrid"))

tgPhones.addTier(tgWords.tierDict["word"])
tgPhones.save(join(path, "bobby.TextGrid"))
