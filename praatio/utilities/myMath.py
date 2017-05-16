'''
Created on Jan 6, 2016

@author: Tim
'''

import math


def medianFilterTimeSeriesData(featureTimeList, filterAmount, index,
                               useEdgePadding):
    '''
    Median filter time-stamped data values.
    
    It's ok to have other values in the list. eg
    featureTimeList: [(time_0, .., featureA_0, ..),
                      (time_1, .., featureA_1, ..),
                      ..]
    '''
    featureTimeList = [list(row) for row in featureTimeList]
    featValues = [row[index] for row in featureTimeList]
    featValues = medianFilter(featValues, filterAmount,
                              useEdgePadding)
    assert(len(featureTimeList) == len(featValues))
    outputList = [piRow[:index] + [f0Val, ] + piRow[index + 1:]
                  for piRow, f0Val in zip(featureTimeList, featValues)]
        
    return outputList


def medianFilter(dist, window, useEdgePadding):
    
    offset = int(math.floor(window / 2.0))
    length = len(dist)

    returnList = []
    for x in range(length):
        dataToFilter = []
        # If using edge padding or if 0 <= context <= length
        if useEdgePadding or (((0 <= x - offset) and (x + offset < length))):
            
            preContext = []
            currentContext = [dist[x], ]
            postContext = []
            
            lastKnownLargeIndex = 0
            for y in range(1, offset + 1):  # 1-based
                if x + y >= length:
                    if lastKnownLargeIndex == 0:
                        largeIndexValue = x
                    else:
                        largeIndexValue = lastKnownLargeIndex
                else:
                    largeIndexValue = x + y
                    lastKnownLargeIndex = x + y
                
                postContext.append(dist[largeIndexValue])
                
                if x - y < 0:
                    smallIndexValue = 0
                else:
                    smallIndexValue = x - y
                    
                preContext.insert(0, dist[smallIndexValue])
                
            dataToFilter = preContext + currentContext + postContext
            value = _median(dataToFilter)
        else:
            value = dist[x]
        returnList.append(value)
        
    return returnList


def _median(valList):
    
    valList = valList[:]
    valList.sort()
    
    if len(valList) % 2 == 0:  # Even
        i = int(len(valList) / 2.0)
        medianVal = (valList[i - 1] + valList[i]) / 2.0
    else:  # Odd
        i = int(len(valList) / 2.0)
        medianVal = valList[i]
        
    return medianVal


def rms(intensityValues):
    intensityValues = [val ** 2 for val in intensityValues]
    meanVal = sum(intensityValues) / len(intensityValues)
    return math.sqrt(meanVal)
