'''
For handling shorter, less complicated praat data files

Created on Nov 26, 2015

@author: tmahrt
'''


class PointProcess(object):
    
    def __init__(self, pointList, minTime=0, maxTime=None):
        if maxTime is None:
            maxTime = max(pointList)
            
        self.pointList = pointList
        self.minTime = minTime
        self.maxTime = maxTime
        
    def save(self, fn):
        header = ('File type = "ooTextFile"\n'
                  'Object class = "PointProcess"\n'
                  '\n%f\n%f\n%d')
        header %= (self.minTime, self.maxTime, len(self.pointList))
        
        strPoints = "\n".join([str(val) for val in self.pointList])
        
        outputStr = "%s\n%s" % (header, strPoints)
        
        open(fn, "w").write(outputStr)
    
    def getPointsInInterval(self, start, stop, startIndex = 0):
    
        returnPointList = []
        for i, time in enumerate(self.pointList[startIndex:]):
            if time >= start:
                if time <= stop:
                    returnPointList.append(time)
                else:
                    break
        
        return returnPointList
        

def openPointProcess(fn):
    data = open(fn, "rU").read()
    if "xmin" in data[:100]:  # Kindof lazy
        dataList = _parseNormalPointProcess(fn)
    else:
        dataList = _parseShortPointProcess(fn)
    
    return dataList


def _parseNormalPointProcess(fn):
    data = open(fn, "rU").read()
    
    chunkedData = data.split("\n", 7)
    
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
    
    return PointProcess(dataList, minT, maxT)


def _parseShortPointProcess(fn):
    data = open(fn, "rU").read()
    
    chunkedData = data.split("\n", 6)
    
    data = chunkedData[-1]
    maxT = chunkedData[-3]
    minT = chunkedData[-4]
    
    minT, maxT = float(minT), float(maxT)
    
    dataList = data.split('\n')
    dataList = [float(val) for val in dataList if val.strip() != '']
    
    return PointProcess(dataList, minT, maxT)
