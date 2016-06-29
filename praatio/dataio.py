'''
For handling shorter, less complicated praat data files

Created on Nov 26, 2015

@author: tmahrt
'''

import io

POINT = "PointProcess"
PITCH = "PitchTier"
DURATION = "DurationTier"
 

class PointObject(object):
    
    def __init__(self, pointList, objectClass, minTime=0, maxTime=None):
        if maxTime is None:
            maxTime = max(pointList)
            
        self.pointList = pointList
        self.objectClass = objectClass
        self.minTime = minTime if minTime > 0 else 0
        self.maxTime = maxTime
    
    def __eq__(self, other):
        isEqual = True
        isEqual &= self.objectClass == other.objectClass
        isEqual &= self.minTime == other.minTime
        isEqual &= self.maxTime == other.maxTime
        
        for selfEntry, otherEntry in zip(self.pointList, other.pointList):
            isEqual &= selfEntry == otherEntry
        
        return isEqual
    
    def save(self, fn):
        header = ('File type = "ooTextFile"\n'
                  'Object class = "%s"\n'
                  '\n%s\n%s\n%d')
        header %= (self.objectClass, repr(self.minTime), repr(self.maxTime),
                   len(self.pointList))
        
        tmp = [repr(val) for entry in self.pointList for val in entry]
        strPoints = "\n".join(tmp)
        
        outputStr = u"%s\n%s\n" % (header, strPoints)
        
        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(outputStr)
    
    def getPointsInInterval(self, start, stop, startIndex=0):
    
        returnPointList = []
        for entry in self.pointList[startIndex:]:
            time = entry[0]
            if time >= start:
                if time <= stop:
                    returnPointList.append(time)
                else:
                    break
        
        return returnPointList


class PointObject1D(PointObject):
    '''Points that only carry temporal information'''

    def __init__(self, pointList, objectClass, minTime=0, maxTime=None):

        assert(objectClass != PITCH)
        assert(objectClass != DURATION)
        
        super(PointObject1D, self).__init__(pointList, objectClass,
                                            minTime, maxTime)


class PointObject2D(PointObject):
    '''Points that carry a temporal value and some other value'''

    def __init__(self, pointList, objectClass, minTime=0, maxTime=None):

        assert(objectClass != POINT)

        super(PointObject2D, self).__init__(pointList, objectClass,
                                            minTime, maxTime)


def open1DPointObject(fn):
    with io.open(fn, "r", encoding='utf-8') as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index('=', start)
            except ValueError:
                break
            
            timeVal, start = _getNextValue(data, start)
            pointVal, start = _getNextValue(data, start)
            dataList.append([float(timeVal), float(pointVal), ])
        
        po = PointObject2D(dataList, objectType, minT, maxT)
    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataList = data.split('\n')
        dataList = [[float(val), ] for val in dataList if val.strip() != '']
        po = PointObject1D(dataList, objectType, minT, maxT)
    
    return po


def open2DPointObject(fn):
    with io.open(fn, "r", encoding='utf-8') as fd:
        data = fd.read()
    if "xmin" in data[:100]:  # Kindof lazy
        data, objectType, minT, maxT = _parseNormalHeader(fn)

        start = 0
        dataList = []
        while True:
            try:
                start = data.index('=', start)
            except ValueError:
                break
            
            pointVal, start = _getNextValue(data, start)
            dataList.append([float(pointVal), ])
        
        po = PointObject2D(dataList, objectType, minT, maxT)
        
    else:
        data, objectType, minT, maxT = _parseShortHeader(fn)
        dataList = data.split('\n')
        dataList = [(float(dataList[i]), float(dataList[i + 1]))
                    for i in range(0, len(dataList), 2)
                    if dataList[i].strip() != '']
        po = PointObject2D(dataList, objectType, minT, maxT)
    
    return po


def _parseNormalHeader(fn):
    with io.open(fn, "r", encoding='utf-8') as fd:
        data = fd.read()
    
    chunkedData = data.split("\n", 7)
    
    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()
    
    data = chunkedData[-1]
    maxT = chunkedData[-4].split("=")[-1].strip()
    minT = chunkedData[-5].split("=")[-1].strip()
    minT, maxT = float(minT), float(maxT)
    
    return data, objectType, minT, maxT


def _getNextValue(data, start):
    end = data.index('\n', start)
    value = data[start + 1:end]
    return value, end


def _parseShortHeader(fn):
    with io.open(fn, "r", encoding='utf-8') as fd:
        data = fd.read()
    
    chunkedData = data.split("\n", 6)
    
    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()
    
    data = chunkedData[-1]
    maxT = chunkedData[-3]
    minT = chunkedData[-4]
    
    minT, maxT = float(minT), float(maxT)
    
    return data, objectType, minT, maxT
