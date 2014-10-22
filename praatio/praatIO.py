'''
Created on Apr 15, 2013

@author: timmahrt
'''

import re
import copy
import functools

import codecs

from os.path import join

# Can only handle interval tiers at the moment
INTERVAL_TIER = "IntervalTier"


def _getMinInTupleList(timestampList):
    return min([float(subList[0]) for subList in timestampList])


def _getMaxInTupleList(timestampList):
    return max([float(subList[1]) for subList in timestampList])


def _morphFunc(fromTier, toTier):
    for fromEntry, toEntry in zip(fromTier.entryList, toTier.entryList):
        
        fromStart, fromEnd, fromLabel = fromEntry
        toStart, toEnd, toLabel = toEntry
        
        # Silent pauses are not manipulated to the target destination
        if fromLabel == 'sp' or fromLabel == '':
            tmpStart = fromStart
            tmpEnd = fromEnd
        else:
            tmpStart = toStart
            tmpEnd = toEnd

        yield tmpStart, tmpEnd, fromLabel


def _manipulateFunc(fromTier, modFunc, filterFunc):
    for fromEntry in fromTier.entryList:
        
        fromStart, fromEnd, fromLabel = fromEntry
        
        # Silent pauses are not manipulated to the target destination
        if fromLabel == 'sp' or fromLabel == '' or not filterFunc(fromLabel):
            tmpStart = fromStart
            tmpEnd = fromEnd
        else:
            tmpStart, tmpEnd = modFunc(fromStart, fromEnd)
            
        yield tmpStart, tmpEnd, fromLabel


def _manipulate(tier, iterateFunc):
    '''
    A generic function for manipulating tiers
    
    The provided /iterateFunc/ specifies the new values for old textgrid regions
    
    The job of this function is to determine the new location of each textgrid
    intervals (taking into account the other textgrid intervals)
    '''
    adjustedEntryList = []
    adjustAmount = 0.0 # Chains adjustments from prior manipulations onto later ones
    for tmpStart, tmpEnd, fromLabel in iterateFunc():

        tmpAdjustAmount = (tmpEnd - tmpStart)
        
        adjustedStart = adjustAmount
        adjustedEnd = adjustAmount + tmpAdjustAmount
        
        adjustAmount += tmpAdjustAmount
        
        adjustedEntryList.append( [adjustedStart, adjustedEnd, fromLabel] )
        
    adjustedTier = TextgridTier(tier.name, adjustedEntryList, tier.tierType)           
    
    return adjustedTier


def _intervalOverlapCheck(interval, cmprInterval):
    '''Checks whether two intervals overlap'''
    
    startTime, endTime, label = interval
    cmprStartTime, cmprEndTime, cmprLabel = cmprInterval
    
    return (float(startTime) <= float(cmprEndTime) and 
            float(endTime) >= float(cmprStartTime))


class TimelessTextgridTierException(Exception):
    
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


class BadIntervalError(Exception):
    
    def __init__(self, start, stop, label):
        self.start = start
        self.stop = stop
        self.label = label
        
    def __str__(self):
        return "Problem with interval--could not create textgrid (%s,%s,%s)" % (self.start, self.stop, self.label)


class TextgridTier():
    
    
    def __init__(self, name, entryList, tierType, minT=None, maxT=None):
        
        # Prevent poorly-formed textgrids from being created
        for entry in entryList:
            if float(entry[0]) > float(entry[1]):
                print "Anomaly: startTime=%f, stopTime=%f, label=%s" % (entry[0], entry[1], entry[2])
            assert(float(entry[0]) < float(entry[1]))

        
        # Remove whitespace
        tmpEntryList = []
        for start, stop, label in entryList:
            tmpEntryList.append( (start, stop, label.strip()))
        entryList = tmpEntryList
        
        self.name = name
        self.entryList = entryList
        self.tierType = tierType
        
        if minT != None and maxT != None:
            if entryList == None or entryList == []:
                entryList.append( [minT, maxT, ""] )
        elif entryList != None and entryList != []:
            minT = _getMinInTupleList(entryList)
            maxT = _getMaxInTupleList(entryList)
        else:
            # Need to have some timing information to create a textgrid tier
            raise TimelessTextgridTierException()
            
        self.minTimestamp = minT
        self.maxTimestamp = maxT
        
        # If an entry list contains "holes"-- fill them in
        self.entryList = self._fillInBlanks("", self.minTimestamp, self.maxTimestamp)
    
    
    def insertInterval(self, startTime, endTime, label):
        interval = (startTime, endTime, label)
        
        # True if any existing times overlap with the new insertion time
        matchList = [ _intervalOverlapCheck(interval, oldInterval) for oldInterval in self.entryList]
        print matchList
        print matchList.count(True)
        print self.entryList[matchList.index(True)]
        assert(matchList.count(True) == 0 or (matchList.count(True) == 1 and self.entryList[matchList.index(True)][2] == ""))
        
        # For inserting into an 'empty' textgrid
        if matchList.count(True) == 0:
            self.entryList.append([startTime, endTime, label])
            self.entryList.sort()
            
        # For inserting into a textgrid with content
        elif matchList.count(True) == 1:
            i = matchList.index(True)
            oldStart, oldStop, oldLabel = self.entryList[i]
        
            subEntryList = []
            if oldStart != startTime:
                subEntryList.append([oldStart, startTime, ""])
            subEntryList.append([startTime, endTime, label])
            if oldStop != endTime:
                subEntryList.append([endTime, oldStop, ""]) 
    
            newEntryList = self.entryList[:i] + subEntryList + self.entryList[i+1:]
            self.entryList = newEntryList
            
    
    def getDuration(self):
        return self.maxTimestamp - self.minTimestamp
    
    
    def getSegmentDurations(self):
        return [float(subList[1]) - float(subList[0]) for subList in self.entryList]
    
        
    def getText(self):
        '''
        Prints each entry in the tier on a separate line w/ timing info
        '''
        text = ""
        text += '"%s"\n' % self.tierType
        text += '"%s"\n' % self.name
        text += '%s\n%s\n%s\n' % (self.minTimestamp, self.maxTimestamp, len(self.entryList))
        
        for startTime, endTime, label in self.entryList:
            text += '%s\n%s\n"%s"\n' % (startTime, endTime, label)
            
        return text


    def getIntervals(self, includeSilence, filterFunc=None):
        extractList = []
        for start, end, label in self.entryList:
            if (not includeSilence) and (label != "" and label != "sp"):
                if filterFunc == None or (filterFunc != None and filterFunc(label)):
                    extractList.append((start,end,label))
                    
        return extractList
    

    def getSpeakingTime(self, blankLabel=None):
        '''
        Calculates the combined duration of every interval that is not silence
        '''
        
        if blankLabel == None:
            blankLabel = ""
        
        duration = 0.0
        for start, end, label in self.entryList:
            if label != blankLabel:
                duration += end - start
        
        return duration
    

    def _fillInBlanks(self, blankLabel, startTime=None, endTime=None):
        if startTime == None:
            startTime = self.minTimestamp
            
        if endTime == None:
            endTime = self.maxTimestamp
        
        # Special case: empty textgrid
        if len(self.entryList) == 0:
            self.entryList.append( (startTime, endTime, blankLabel))
        
        # For the current entryList, fill in any gaps between two items
        entry = self.entryList[0]
        newEntryList = [entry]
        prevEnd = float(entry[1])
        for entry in self.entryList[1:]:
            newStart = float(entry[0])
            newEnd = float(entry[1])
            if prevEnd < newStart:
                newEntryList.append( (prevEnd, newStart, blankLabel) )
            newEntryList.append(entry)
            prevEnd = newEnd
        
        # Special case: If there is a gap at the start of the file
        assert( float(self.entryList[0][0]) >= float(startTime) )
        if float(newEntryList[0][0]) > float(startTime):
            newEntryList.insert(0, (startTime, newEntryList[0][0], blankLabel))
        
        # Special case -- if there is a gap at the end of the file
        if not float(newEntryList[-1][1]) <= float(endTime):
            print newEntryList[-1][1], endTime
        assert( float(newEntryList[-1][1]) <= float(endTime) )
        if float(newEntryList[-1][1]) < float(endTime):
            newEntryList.append( (newEntryList[-1][1], endTime, blankLabel) ) 

        newEntryList.sort()

        return newEntryList
    

    def fillInBlanks(self, blankLabel, startTime=None, endTime=None):
        '''
        Fills-in an improperly made textgrid with blank entries
        '''
        newEntryList = self._fillInBlanks(blankLabel, startTime, endTime)
        
        newTier = TextgridTier(self.name, newEntryList, self.tierType)
        
        return newTier
    
    
    def editLabels(self, editFunc):
        
        newEntryList = []
        for start, stop, label in self.entryList:
            newEntryList.append( (start, stop, editFunc(label)))
    
        newTier = TextgridTier(self.name, newEntryList, self.tierType)
            
        return newTier
    
    
    def sort(self):
        self.entryList.sort()
        

    def morph(self, targetTier):
        return _manipulate(self, functools.partial(_morphFunc, self, targetTier))
    
    
    def manipulate(self, modFunc, filterFunc):
        return _manipulate(self, functools.partial(_manipulateFunc, self, modFunc, filterFunc))
    
    
    def setTimeFromZero(self, tareTime=None):
        '''
        Adjusts all timestamps by a given value
        
        By default, it assumes that the smallest timestamp should be adjusted 
        to zero.
        '''
        if tareTime == None:
            firstTimestamp = self.minTimestamp
        entryList = [(start - firstTimestamp, end - firstTimestamp, label)  for start, end, label in self.entryList]

        newTier = TextgridTier(self.name, entryList, self.tierType)
        
        return newTier
    
    
    def find(self, matchLabel, substrMatchFlag=False):
        '''
        Returns all intervals that match the given label
        '''
        returnList = []
        for start, stop, label in self.entryList:
            if not substrMatchFlag:
                if label == matchLabel:
                    returnList.append((start, stop, label))
            else:
                if matchLabel in label:
                    returnList.append((start, stop, label))
        
        return returnList
    
    
    def reSearch(self, matchLabel):
        returnList = []
        for start, stop, label in self.entryList:
            matchList = re.findall(matchLabel, label, re.I)
            if matchList != []:
                returnList.append( (start, stop, label) )
                print label
        
        return returnList
    
            
    def crop(self, cropStart, cropEnd, strictFlag, softFlag):
        '''
        Creates a new tier containing all entries that fit inside a new, given interval
        
        If strictFlag = True, only intervals wholly contained by the crop period
            will be kept
            
        If softFlag = True, the crop period will be stretched to the ends of intervals
            that are only partially contained by the crop period
            
        If both strictFlag and softFlag are set to false, partially contained tiers
            will be truncated in the output tier.
        '''
        newEntryList = []
        cutTStart = 0
        cutTWithin = 0
        cutTEnd = 0
        firstIntervalKeptProportion = 0
        lastIntervalKeptProportion = 0
        copy.deepcopy(self.entryList)
        
        for entry in self.entryList:
            matchedEntry = None
            
            intervalStart = entry[0]
            intervalEnd = entry[1]
            intervalLabel = entry[2]
            
            # Don't need to investigate if the interval is before or after
            # the crop region
            if intervalEnd <= cropStart or intervalStart >= cropEnd:
                continue
            
            # Determine if the current subEntry is wholly contained
            # within the superEntry
            if intervalStart >= cropStart and intervalEnd <= cropEnd:
                matchedEntry = entry
                if matchedEntry[0] >= matchedEntry[1]:
                    print 'A: ', matchedEntry
            
            # If it is only partially contained within the superEntry AND 
            # inclusion is 'soft', include it anyways
            elif softFlag and (intervalStart >= cropStart or intervalEnd <= cropEnd):
                matchedEntry = entry
                if matchedEntry[0] >= matchedEntry[1]:
                    print 'B: ', matchedEntry
            
            # If not strict, include partial tiers on the edges
            # -- regardless, record how much information was lost
            #        - for strict=True, the total time of the cut interval
            #        - for strict=False, the portion of the interval that lies
            #            outside the new interval

            # The current interval stradles the end of the new interval
            elif intervalStart >= cropStart and intervalEnd > cropEnd:
#                 print intervalStart, intervalEnd, cropStart, cropEnd
                cutTEnd = intervalEnd - cropEnd
                lastIntervalKeptProportion = (cropEnd - intervalStart) / (intervalEnd - intervalStart)

                if not strictFlag:
                    matchedEntry = (intervalStart, cropEnd, intervalLabel)
                    if matchedEntry[0] >= matchedEntry[1]:
                        print 'C: ', matchedEntry
                    
                else:
                    cutTWithin += cropEnd - cropStart
            
            # The current interval stradles the start of the new interval
            elif intervalStart < cropStart and intervalEnd <= cropEnd:
                cutTStart = cropStart - intervalStart
                firstIntervalKeptProportion = (intervalEnd - cropStart) / (intervalEnd - intervalStart)
                if not strictFlag:
                    matchedEntry = [cropStart, intervalEnd, intervalLabel]
                    if matchedEntry[0] >= matchedEntry[1]:
                        print 'D: ', matchedEntry
                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval contains the new interval completely
            elif intervalStart <= cropStart and intervalEnd >= cropEnd:
                if not strictFlag:
                    matchedEntry = (cropStart, cropEnd, intervalLabel)
                    if matchedEntry[0] >= matchedEntry[1]:
                        print 'E: ', matchedEntry
                else:
                    cutTWithin += cropEnd - cropStart
                        
            if matchedEntry != None:
                if matchedEntry[0] >= matchedEntry[1]:
                    print 'F: ', matchedEntry
                newEntryList.append(matchedEntry)

        if len(newEntryList) == 0:
            newEntryList.append( (0, cropEnd-cropStart, ""))

        # Create subtier
        subTier = TextgridTier(self.name, newEntryList, self.tierType)
        return subTier, cutTStart, cutTWithin, cutTEnd, firstIntervalKeptProportion, lastIntervalKeptProportion
    
    
    def mergeSilences(self, minTimestamp, maxTimestamp):
        
        # First remove all silences
        newEntryList = []
        for entry in self.entryList:
            label = entry[2]
            if label == "":
                continue
            else:
                newEntryList.append(entry)
        
        # Fill in the empty spaces between non-empty spaces
        if newEntryList == []:
            newEntryList = [(minTimestamp, maxTimestamp, ""),]
            newTier = TextgridTier(self.name, newEntryList, self.tierType)
        else:
            newTier = TextgridTier(self.name, newEntryList, self.tierType)
            newTier = newTier.fillInBlanks("", minTimestamp, maxTimestamp)

        return newTier
    
    
    def appendTier(self, tier, timeRelativeFlag):
        
        entryList = copy.deepcopy(self.entryList)
        for start, stop, label in tier.entryList:
            
            if timeRelativeFlag == True:
                entryList.append( (start + self.maxTimestamp, stop + self.maxTimestamp, label) )
            else:
                entryList.append( (start, stop, label) )
            
        
        return TextgridTier(self.name, entryList, self.tierType)
    
        
    def offsetTimestamps(self, startOffset, stopOffset, allowOvershoot=False):
        '''
        Modifies all timestamps by a constant amount
        
        Can modify the interval start independent of the interval end
        
        If allowOvershoot is True, an interval can go beyond the duration
        of the textgrid (I can't imagine why this should be the case) 
        '''
        
        newEntryList = []
        for start, stop, label in self.entryList:
            
            newStart = startOffset+start
            if newStart < 0:
                newStart = 0
            
            newStop = stopOffset+stop
            if newStop > self.maxTimestamp and not allowOvershoot:
                newStop = self.maxTimestamp
            
            newEntryList.append( (newStart, newStop, label) )
            
        newMax = max([self.maxTimestamp, _getMaxInTupleList(newEntryList)])
        return TextgridTier(self.name, newEntryList, self.tierType, 0, newMax)
    
        
        
class Textgrid():
    
    
    def __init__(self):
        self.tierNameList = [] # Preserves the order of the tiers
        self.tierDict = {}
    
        self.minTimestamp = None
        self.maxTimestamp = None
    
    
    def getContainedLabels(self, superTier):
        '''
        Returns a list of tiers that fall under each label in the given superTier
        
        A typical example would be all of the phones in phoneTier that fall 
        under each word in wordTier.
        
        Each interval gets its own dictionary of tiers.
        '''
        
        returnList = []
        tier = self.tierDict[superTier]
        for startTime, endTime, label in tier.entryList:
            tierNameList = copy.deepcopy(self.tierNameList)
            tierNameList.pop(tierNameList.index(superTier))
            
            outputDict = {}
            for subTier in tierNameList:
                containedList = []
                tier = self.tierDict[subTier]
                for tmpStart, tmpEnd, label in tier.entryList:
                    if startTime <= tmpStart:
                        if endTime >= tmpEnd:
                            containedList.append( (tmpStart, tmpEnd, label) )
                        else:
                            break
                outputDict[subTier] = containedList
            returnList.append(outputDict)
            
        return returnList
    
    
    def addTier(self, tier, tierIndex=None):
        
        if tierIndex == None:
            self.tierNameList.append(tier.name)
        else:
            self.tierNameList.insert(tierIndex, tier.name)
        self.tierDict[tier.name] = tier
        
        minV = tier.minTimestamp
        if minV < self.minTimestamp or self.minTimestamp == None:
            self.minTimestamp = minV
        
        maxV = tier.maxTimestamp
        if maxV > self.maxTimestamp or self.maxTimestamp == None:
            self.maxTimestamp = maxV
        
        
    def addTierByList(self, name, tierEntryList, tierType, tierIndex=None):
        try:
            tierEntryList = [(float(start), float(end), label) for start, end, label in tierEntryList ]
        except ValueError:
            raise BadIntervalError(start, end, label)
        newTier = TextgridTier(name, tierEntryList, tierType)
        self.addTier(newTier, tierIndex)
            
    
    def removeTier(self, name):
        self.tierNameList.pop(self.tierNameList.index(name))
        del self.tierDict[name]
        
        
    def removeLabels(self, label, tierNameList=None):
        '''Remove labels from tiers'''
        
        # Remove from all tiers if no tiers are specified
        if tierNameList == None:
            tierNameList = self.tierNameList
        
        tg = Textgrid()
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            
            if tierName in tierNameList:
                newEntryList = [entry for entry in tier.entryList if entry[2] != label]
                tier = TextgridTier(tierName, newEntryList, tier.tierType)
            
            tg.addTier(tier)
        
        return tg
        
    
    def renameTier(self, oldName, newName):
        oldTier = self.tierDict[oldName]
        tierIndex = self.tierNameList.index(oldName)
        self.removeTier(oldName)
        self.addTierByList(newName, oldTier.entryList, oldTier.tierType, tierIndex)
        
        
    def replaceTier(self, name, newTierEntryList):
        oldTier = self.tierDict[name]
        tierIndex = self.tierNameList.index(name)
        self.removeTier(name)
        self.addTierByList(name, newTierEntryList, oldTier.tierType, tierIndex)
        
    
    def save(self, fn):
        
        # Kindof inelegant
        tmpTG = self.fillInBlanks()
        self.tierDict = tmpTG.tierDict
        self.sort()
        
        outputTxt = ""
        outputTxt += 'File type = "ooTextFile short"\n'
        outputTxt += '"TextGrid"\n\n'
        outputTxt += "%s\n%s\n" % (self.minTimestamp, self.maxTimestamp)
        outputTxt += "<exists>\n%d\n" % len(self.tierNameList)
        
        for tierName in self.tierNameList:
            outputTxt += self.tierDict[tierName].getText()
        
        codecs.open(fn, "w", encoding="utf-8").write(outputTxt)


    def crop(self, strictFlag, softFlag, startTime=None, endTime=None):
        
        if startTime == None:
            startTime = self.minTimestamp
            
        if startTime == None:
            endTime = self.maxTimestamp
            
        newTG = Textgrid()
        for tierName in self.tierNameList:
            newTier = self.tierDict[tierName].crop(startTime, endTime, strictFlag, softFlag)[0]
            newTier.sort()
            
            newTG.addTier(newTier)
        
        retTG = newTG.fillInBlanks()
        retTG = retTG.setTimeFromZero()
        
        return retTG

    
    def mergeTiers(self, includeFunc=None, 
                   tierList=None, preserveOtherTiers=True):
        '''
        Combine tiers.
        
        /includeFunc/ regulates which intervals to include in the merging
          with all others being tossed (default tosses silent labels: '')
          
        If /tierList/ is none, combine all tiers.
        '''
        
        if tierList == None:
            tierList = self.tierNameList
            
        if includeFunc == None:
            includeFunc = lambda entryList: not entryList[2] == ''
           
        # Merge tiers
        superEntryList = []
        for tierName in tierList:
            tier = self.tierDict[tierName]
            superEntryList.extend(tier.entryList)
        
        superEntryList = [entry for entry in superEntryList if includeFunc(entry)]
            
        superEntryList.sort()
        
        # Do the merge here
        i = 0
        while i < len(superEntryList) - 1:
            currentEntry = superEntryList[i]
            nextEntry = superEntryList[i+1]
            
            if _intervalOverlapCheck(currentEntry, nextEntry):
                currentStart, currentStop, currentLabel = superEntryList[i]
                nextStart, nextStop, nextLabel = superEntryList.pop(i+1)
                
                newStop = max([currentStop, nextStop])
                newLabel = "%s / %s" % (currentLabel, nextLabel)
                
                superEntryList[i] = (currentStart, newStop, newLabel)
                
            else:
                i += 1
            
        # Create the final textgrid
        tg = Textgrid() 
            
        # Preserve non-merged tiers
        if preserveOtherTiers == True:
            otherTierList = []
            for tierName in self.tierNameList:
                if tierName not in tierList:
                    otherTierList.append(self.tierDict[tierName])

            for tier in otherTierList:
                tg.addTier(tier)

        # Add merged tier
        tierName = "/".join(tierList)
        mergedTier = TextgridTier(tierName, superEntryList, INTERVAL_TIER)
        tg.addTier(mergedTier)
        
        return tg
        
        
    def mergeSilences(self):
        
        tg = Textgrid()
        for tierName in self.tierNameList:
            tg.addTier(self.tierDict[tierName].mergeSilences(self.minTimestamp, self.maxTimestamp))
            
        return tg
    
    
    def fillInBlanks(self):

        tg = Textgrid()
        for tierName in self.tierNameList:
            tg.addTier(self.tierDict[tierName].fillInBlanks("", self.minTimestamp, self.maxTimestamp))    
            
        return tg
    

    def findMatchedTGSubset(self, superTierName, qualifyFunc, strictFlag):
        '''
        Returns intervals that are contained in qualifying superTier intervals
        
        For labeled regions in the super tier that pass the qualifyFunc,
        labeled intervals in the 
        
        If /strictFlag/ is True, only intervals wholly contained within the
        textgrid are included.  Otherwise, partially-contained intervals
        will also be included (but truncated to fit within the super tier).
        '''
        superTier = self.tierDict[superTierName]
        
        newTierNameList = copy.deepcopy(self.tierNameList)
        newTierNameList.pop(newTierNameList.index(superTierName))
        
        for subTierName in newTierNameList:
            subTier = self.tierDict[subTierName]
        
            for superEntry in superTier.entryList:
                if qualifyFunc(superEntry):
                    yield superEntry, subTierName, subTier.createTierSubset(superEntry[0], superEntry[1], strictFlag)


    def createSubtextgrid(self, superTierName, qualifyingFunc, strictFlag):
        
        tierDataDict = {}
        for superEntry, subTierName, subEntry in self.findMatchedTGSubset(superTierName, qualifyingFunc, strictFlag):
            tierDataDict.setdefault(subTierName, [])
            tierDataDict[subTierName].append(subEntry)
        
        tg = Textgrid()
        for tierName, tierData in tierDataDict.items():
            tier = TextgridTier(tierName, tierData, INTERVAL_TIER)
            tg.addTier(tier)
            
        return tg

    
    def findStr(self, tierName, matchStr, substrMatchFlag=False):
        return self.tierDict[tierName].find(matchStr, substrMatchFlag)
    
    
    def findMatchedData(self, dataTupleList, tierName, qualifyFunc=None):
        '''
        Returns all data from dataTupleList in chunks, divided by labeled regions
        
        dataTupleList should be of the form [(value1, time1), (value2, time2),...]
        '''
        if qualifyFunc == None:
            qualifyFunc = lambda label: True # All labels pass
            
        tier = self.tierDict[tierName]
        
        for interval in tier.entryList:
            print "--'%s'" % interval[2]
            intervalDataList = []
            for value, time in dataTupleList:
                if interval[0] <= time and interval[1] >= time:
                    intervalDataList.append( (value, time) )
            yield intervalDataList
            
               
    def getSubtextgrid(self, superTierName, qualifyFunc):
        '''
        Create a tg that includes only a subset of the orig tg entries
        
        So, for example, if you only wanted the labeled portions for every
        instance of "the" or some other word, you could use this to isolate
        those portions (and then extract the text from that entire tier,
        for example)
        
        Deleted segments are indicated in the superTier
        '''
        
        superTier = self.tierDict[superTierName]
        
        # Determine which segments in the subTiers to keep
        tierList = []

        subTierDict = {}
        for superEntry, subTierName, subEntry in self.findMatchedTGSubset(superTierName, qualifyFunc, strictFlag=True):
#             subTierEntryList.append(subEntry)
            if subTierName not in subTierDict.keys():
                subTierDict[subTierName] = []
            subTierDict[subTierName].append(subEntry)
            
        for subTierName, subTierEntryList in subTierDict.items():
            subTier = self.tierDict[subTierName]
            
            # Sort tier by start time (for reasons I do not understand, 
            # the order of the tier gets jumbled)
            subTierEntryList.sort()
            tierList.append( (subTier, subTierName, subTierEntryList, subTier.tierType) )
            
        # Include the superTier in the tierList
        superEntryList = []
        for superEntry in superTier.entryList:
            if qualifyFunc(superEntry):
                superEntryList.append(superEntry)
        tierList.append( (superTier, superTierName, superEntryList, superTier.tierType))
        
        # Make a new textgrid from tierList
        newTG = Textgrid()
        for oldTier, name, tierEntryList, tierType in tierList:
            tier = TextgridTier(name, tierEntryList, tierType)
            tier.maxTimestamp = oldTier.maxTimestamp
            tier.minTimestamp = oldTier.minTimestamp
            
            newTG.addTier(tier)
            
        newTG.maxTimestamp = self.maxTimestamp

        # Although we just created it, we're going to make a new textgrid
        # with the missing data areas (if any) patched with empty intervals
        patchedTG = Textgrid()
        for tierName in newTG.tierNameList:
            tier = newTG.tierDict[tierName]
            
            # The interval should be empty, except for the superTier,
            # where we should indicate that the section was deleted
            # with this script
            if tier.name == superTierName:
                blankText = "/deleted/"
            else:
                blankText = ""
                
            newTier = tier.fillInBlanks(blankText)
            patchedTG.addTierByList(newTier.name, newTier.entryList, newTier.tierType)

        return patchedTG    
    
    
    def setTimeFromZero(self):
        
        zeroedTG = Textgrid()
        for tierName in self.tierNameList:
            newTier = self.tierDict[tierName].setTimeFromZero()
            zeroedTG.addTier(newTier)
            
        return zeroedTG
    
    
    def offsetTimestamps(self, startOffset, stopOffset):
        
        tg = Textgrid()
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            tier = tier.offsetTimestamps(startOffset, stopOffset)
            
            tg.addTier(tier)
        
        return tg
        
    
#     def append(self, tg, timeRelative=False):
#         
#         newTG = Textgrid()
#         
#         for tierName in tg.tierNameList:
#             newTier = tg.tierDict[tierName]
#             if tierName in self.tierNameList:
#                 newTier = self.tierDict[tierName].appendTier(newTier, timeRelative)
#             else:
#                 if timeRelative:
#                     newTier = newTier.offsetTimestamps(self.maxTimestamp)
#             
#                 else:
#                     newTG[tierName] = appendTier


def openTextGrid(fnFullPath):
    
    try:
        data = codecs.open(fnFullPath, "rU", encoding="utf-16").read()
    except UnicodeError:
        data = codecs.open(fnFullPath, "rU", encoding="utf-8").read()
    data = data.replace("\r\n", "\n")
    
    caseA = u"ooTextFile short" in data
    caseB = u"item" not in data   
    if caseA or caseB:
        textgrid = _parseShortTextGrid(data)
    else:
        textgrid = _parseNormalTextGrid(data)
        
    return textgrid


def _parseNormalTextGrid(data):
    '''
    Reads a normal textgrid
    '''
    newTG = Textgrid()
    
    # Toss textgrid header
    data = data.split("item", 1)[1]
    
    # Process each tier individually (will be output to separate folders)
    tierList = data.split("item")[1:]
    for tier in tierList:
        try:
            header, tierData = tier.split("intervals", 1)
        except ValueError:
            print "Could not process tier -- probably a point tier"
            continue
        
        # Get tier name
        tierName = header.split("name = ")[1].split("\n", 1)[0]
        tierName = tierName.strip()[1:-1]
#         tierName = tierName.replace('"', '')
        
        tierEntryList = processIntervalTier(tierData)
        if tierEntryList == []:
            print "Empty tier.  Not sure how to handle this at the moment.  Skipping"
            continue
        newTG.addTierByList(tierName, tierEntryList, 'IntervalTier')
        
    return newTG
    

def _parseShortTextGrid(data):
    '''
    Reads a short textgrid file
    '''
    newTG = Textgrid()
    
    tierList = data.split('"IntervalTier"')[1:]
    
    
    for tierData in tierList:
        tierData = tierData.strip()
        tierDataList = tierData.split("\n")
#         tierName = tierDataList.pop(0).replace('"', '')
        tierName = tierDataList.pop(0)[1:-1]
        startTime = tierDataList.pop(0)
        endTime = tierDataList.pop(0)
        n = tierDataList.pop(0)
        
        startTimeList = [float(time.strip()) for time in tierDataList[0::3]]
        endTimeList = [float(time.strip()) for time in tierDataList[1::3]]
        textList = [text[1:-1] for text in tierDataList[2::3]]
#         textList = [text.replace('"', '').strip() for text in tierDataList[2::3]]
        
        tierEntryList = []
        for triTuple in zip(startTimeList, endTimeList, textList):
            tierEntryList.append(triTuple)
            

        newTG.addTierByList(tierName, tierEntryList, 'IntervalTier')

    return newTG


def processIntervalTier(tierData):
    # Extract segment lengths and values
    tierEntryList = []
    segmentDataList = tierData.split("intervals")[1:]
    for segment in segmentDataList:
        
        segmentList = segment.split("\n", 3)[1:]
        
        lineDict = {}
        for row in segmentList:
            key, value = row.split("=", 1)
            key = key.strip()
            value = value.strip()
            lineDict[key] = value.replace('"', '')
#         
#         # Clean up results
#         lineDict["text"] = lineDict["text"].replace('"', '')
        
        tierEntryList.append( [lineDict[key] for key in ["xmin", "xmax", "text",]] )
        
    return tierEntryList


def readPitchTier(path, fn):
    data = open(join(path, fn), "r").read()
    dataList = data.split("\n")
    
    pitchTierheader = dataList[:6]
    pitchDataList = dataList[6:]
    outputPitchDataList = [(float(pitchValue), float(time)) for time, pitchValue in zip(pitchDataList[::2], pitchDataList[1::2])]

    return pitchTierheader, outputPitchDataList


def writePitchTier(path, fn, pitchHeader, pitchDataList):
    pitchList = pitchHeader + pitchDataList
    
    pitchTxt = "\n".join(pitchList)
    
    open(join(path, fn), "w").write(pitchTxt)



if __name__ == "__main__":
    
    pass




    
    
