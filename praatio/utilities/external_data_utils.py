'''
Created on Jan 6, 2016

@author: Tim

Tools for pairing non-praat data with praat data
'''

from praatio import tgio

def getValuesInLabeledIntervals(tgFN, tierName, dataList, getTimeFunc,
                                nullLabelList=None):
    '''
    Removes values from the dataList that don't appear in labeled intervals
    
    dataList is of the form [[
    
    nullLabelList - labels to ignore in the textgrid.  Defaults to ["",]
    '''
    retValList = []
    
    if nullLabelList == None:
        nullLabelList = ["",]
    
    # Open the textgrid
    tg = tgio.openTextGrid(tgFN)
    tier = tg.tierDict[tierName]
    
    # For each interval, load just the F0 values
    for valueList, label, _, _ in _getValuesForIntervals(dataList,
                                                         tier.entryList,
                                                         getTimeFunc):

        label = label.strip()
        if label == "" or label in nullLabelList:
            continue
        
        piValues = [(f0Val, intVal) for _, f0Val, intVal in valueList]

        retValList.append((label, piValues))
    
    return retValList


def _getValuesForIntervals(dataList, entryList, getTimeFunc):
    for start, stop, label in entryList:
        
        subDataList = _getAllValuesInTime(start, stop, dataList, getTimeFunc)
        if subDataList == []:
            print("No data for interval")
            print("%s, %s, %f, %f" %
                  (",".join(subDataList), label, start, stop))
        
        yield subDataList, label, start, stop
        
        
def _getAllValuesInTime(startTime, stopTime, dataTuple, getTimeFunc):
    
    returnTuple = []
    for dataRow in dataTuple:
        time = getTimeFunc(dataRow)
        if time >= startTime and time <= stopTime:
            returnTuple.append(dataRow)
            
    return returnTuple
