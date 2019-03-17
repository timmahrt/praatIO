'''
Various math utilities
'''

import math


def filterTimeSeriesData(filterFunc, featureTimeList, windowSize, index,
                               useEdgePadding):
    '''
    Filter time-stamped data values within a window
    
    filterFunc could be medianFilter() or znormFilter()

    It's ok to have other values in the list. eg
    featureTimeList: [(time_0, .., featureA_0, ..),
                      (time_1, .., featureA_1, ..),
                      ..]
    '''
    featureTimeList = [list(row) for row in featureTimeList]
    featValues = [row[index] for row in featureTimeList]
    featValues = filterFunc(featValues, windowSize,
                            useEdgePadding)
    assert(len(featureTimeList) == len(featValues))
    outputList = [piRow[:index] + [f0Val, ] + piRow[index + 1:]
                  for piRow, f0Val in zip(featureTimeList, featValues)]
        
    return outputList


def znormalizeSpeakerData(featureTimeList, index, filterZeroValues):
    '''
    znormalize time series data

    The idea is to normalize each speaker separately to be able
    to compare data across several speakers for speaker-dependent
    data like pitch range

    To normalize a speakers data within a local window, use filterTimeSeriesData()

    filterZeroValues: if True, don't consider zero values in the mean and stdDev
      (recommended value for data like pitch or intensity)
    '''
    featureTimeList = [list(row) for row in featureTimeList]
    featValues = [row[index] for row in featureTimeList]

    if not filterZeroValues:
        featValues = znormalizeData(featValues)
    else:
        featValuesNoZeroes = [val for val in featValues if val != '']
        meanVal = mean(featValuesNoZeroes)
        stdDevVal = stdDev(featValuesNoZeroes)

        featValues = [(val - meanVal) / stdDevVal if val > 0 else 0 for val in featValues]

    assert(len(featureTimeList) == len(featValues))
    outputList = [piRow[:index] + [val, ] + piRow[index + 1:]
                  for piRow, val in zip(featureTimeList, featValues)]

    return outputList


def medianFilter(dist, window, useEdgePadding):
    '''
    median filter each value in a dataset; filtering occurs within a given window

    Median filtering is used to "smooth" out extreme values.  It can be useful if
    your data has lots of quick spikes.  The larger the window, the flatter the output
    becomes.
    Given:
    x = [1 1 1 9 5 2 4 7 4 5 1 5]
    medianFilter(x, 5, False)
    >> [1 1 1 2 4 5 4 4 4 5 1 5]
    '''
    return _stepFilter(median, dist, window, useEdgePadding)


def znormWindowFilter(dst, window, useEdgePadding, filterZeroValues):
    '''
    z-normalize each value in a dataset; normalization occurs within a given window

    If you suspect that events are sensitive to local changes, (e.g. local changes in pitch
    are more important absolute differences in pitch) then using windowed
    znormalization is appropriate.

    See znormalizeData() for more information on znormalization.
    '''

    def znormalizeCenterVal(valList):
        valToNorm = valList[int(len(valList) / 2.0)]
        return (valToNorm - mean(valList)) / stdDev(valList)

    if not filterZeroValues:
        filteredOutput = _stepFilter(znormalizeCenterVal, dist, window, useEdgePadding)
    else:
        zeroIndexList = []
        nonzeroValList = []
        for i, val in enumerate(dst):
            if val > 0.0:
                nonzeroValList.append(val)
            else:
                zeroIndexList.append(i)

        filteredOutput = _stepFilter(znormalizeCenterVal, nonzeroValList, window, useEdgePadding)

        for i in zeroIndexList:
            filteredOutput.insert(i, 0.0)

    return filteredOutput


def _stepFilter(filterFunc, dist, window, useEdgePadding):
    
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
            value = filterFunc(dataToFilter)
        else:
            value = dist[x]
        returnList.append(value)
        
    return returnList


def median(valList):
    
    valList = valList[:]
    valList.sort()
    
    if len(valList) % 2 == 0:  # Even
        i = int(len(valList) / 2.0)
        medianVal = (valList[i - 1] + valList[i]) / 2.0
    else:  # Odd
        i = int(len(valList) / 2.0)
        medianVal = valList[i]
        
    return medianVal


def mean(valList):
    return sum(valList) / float(len(valList))


def stdDev(valList):
    meanVal = mean(valList)
    squaredSum = sum([(val - meanVal) ** 2 for val in valList])

    return math.sqrt(squaredSum / float(len(valList) - 1))


def znormalizeData(valList):
    '''
    Given a list of floats, return the z-normalized values of the floats

    The formula is: z(v) = (v - mean) / stdDev
    In effect, this scales all values to the range [-4, 4].
    It can be used, for example, to compare the pitch values of different speakers who
    naturally have different pitch ranges.
    '''
    valList = valList[:]
    meanVal = mean(valList)
    stdDevVal = stdDev(valList)

    return [(val - meanVal) / stdDevVal for val in valList]


def rms(intensityValues):
    '''Return the root mean square for the input set of values'''
    intensityValues = [val ** 2 for val in intensityValues]
    meanVal = sum(intensityValues) / len(intensityValues)
    return math.sqrt(meanVal)
