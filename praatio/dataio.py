'''
For handling shorter, less complicated praat data files

Created on Nov 26, 2015

@author: tmahrt
'''

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
        
        outputStr = "%s\n%s\n" % (header, strPoints)
        
        open(fn, "w").write(outputStr)
    
    def getPointsInInterval(self, start, stop, startIndex=0):
    
        returnPointList = []
        for time in self.pointList[startIndex:]:
            if time >= start:
                if time <= stop:
                    returnPointList.append(time)
                else:
                    break
        
        return returnPointList
        

def openPointObject(fn):
    data = open(fn, "rU").read()
    if "xmin" in data[:100]:  # Kindof lazy
        dataList = _parseNormalPointObject(fn)
    else:
        dataList = _parseShortPointObject(fn)
    
    return dataList


def _parseNormalPointObject(fn):
    data = open(fn, "rU").read()
    
    chunkedData = data.split("\n", 7)
    
    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()
    
    data = chunkedData[-1]
    maxT = chunkedData[-4].split("=")[-1].strip()
    minT = chunkedData[-5].split("=")[-1].strip()
    minT, maxT = float(minT), float(maxT)
    
    start = 0
    dataList = []
    while True:
        try:
            start = data.index('=', start)
        except ValueError:
            break
        
        end = data.index('\n', start)
        pointVal = data[start + 1:end]
        dataList.append(float(pointVal))
        start = end
    
    return PointObject(dataList, objectType, minT, maxT)


def _parseShortPointObject(fn):
    data = open(fn, "rU").read()
    
    chunkedData = data.split("\n", 6)
    
    objectType = chunkedData[1].split("=")[-1]
    objectType = objectType.replace('"', "").strip()
    
    data = chunkedData[-1]
    maxT = chunkedData[-3]
    minT = chunkedData[-4]
    
    minT, maxT = float(minT), float(maxT)
    
    dataList = data.split('\n')
    dataList = [float(val) for val in dataList if val.strip() != '']
    
    return PointObject(dataList, objectType, minT, maxT)
