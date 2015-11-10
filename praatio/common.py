'''
Created on Oct 30, 2015

@author: tmahrt
'''

def findAll(txt, subStr):
    
    indexList = []
    index = 0
    while True:
        try:
            index = txt.index(subStr, index)
        except ValueError:
            break
        indexList.append(int(index))
        index += 1
    
    return indexList
