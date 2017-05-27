'''
Functions for reading/writing/manipulating textgrid files

Created on Apr 15, 2013

@author: timmahrt
'''

import re
import copy
import io
import wave

from praatio.utilities import utils

INTERVAL_TIER = "IntervalTier"
POINT_TIER = "TextTier"
MIN_INTERVAL_LENGTH = 0.00000001  # Arbitrary threshold


def _getWavDuration(wavFN):
    "For internal use.  See praatio.audioio.WavQueryObj() for general use."
    audiofile = wave.open(wavFN, "r")
    params = audiofile.getparams()
    framerate = params[2]
    nframes = params[3]
    duration = float(nframes) / framerate
    
    return duration


def _fillInBlanks(tier, blankLabel="", startTime=None, endTime=None):
    '''
    Fills in the space between intervals with empty space
    
    This is necessary to do when saving to create a well-formed textgrid
    '''
    if startTime is None:
        startTime = tier.minTimestamp
        
    if endTime is None:
        endTime = tier.maxTimestamp
    
    # Special case: empty textgrid
    if len(tier.entryList) == 0:
        tier.entryList.append((startTime, endTime, blankLabel))
    
    # Create a new entry list
    entryList = tier.entryList[:]
    entry = entryList[0]
    prevEnd = float(entry[1])
    newEntryList = [entry]
    for entry in entryList[1:]:
        newStart = float(entry[0])
        newEnd = float(entry[1])
        
        if prevEnd < newStart:
            newEntryList.append((prevEnd, newStart, blankLabel))
        newEntryList.append(entry)
        
        prevEnd = newEnd
    
    # Special case: If there is a gap at the start of the file
    assert(float(newEntryList[0][0]) >= float(startTime))
    if float(newEntryList[0][0]) > float(startTime):
        newEntryList.insert(0, (startTime, newEntryList[0][0], blankLabel))
    
    # Special case -- if there is a gap at the end of the file
    if endTime is not None:
        assert(float(newEntryList[-1][1]) <= float(endTime))
        if float(newEntryList[-1][1]) < float(endTime):
            newEntryList.append((newEntryList[-1][1], endTime, blankLabel))

    newEntryList.sort()

    return IntervalTier(tier.name, newEntryList,
                        tier.minTimestamp, tier.maxTimestamp)


def _removeUltrashortIntervals(tier, minLength):
    '''
    Remove intervals that are very tiny
    
    Doing many small manipulations on intervals can lead to the creation
    of ultrashort intervals (e.g. 1*10^-15 seconds long).  This function
    removes such intervals.
    '''
    
    # First, remove tiny intervals
    newEntryList = []
    j = 0  # index to newEntryList
    for start, stop, label in tier.entryList:
        
        if stop - start < minLength:
            # Correct ultra-short entries
            if len(newEntryList) > 0:
                lastStart, _, lastLabel = newEntryList[j - 1]
                newEntryList[j - 1] = (lastStart, stop, lastLabel)
        else:
            # Special case: the first entry in oldEntryList was ultra-short
            if len(newEntryList) == 0 and start != 0:
                newEntryList.append((0, stop, label))
            # Normal case
            else:
                newEntryList.append((start, stop, label))
            j += 1
    
    # Next, shift near equivalent tiny boundaries
    j = 0
    while j < len(newEntryList) - 1:
        diff = abs(newEntryList[j][1] - newEntryList[j + 1][0])
        if diff > 0 and diff < MIN_INTERVAL_LENGTH:
            newEntryList[j] = (newEntryList[j][0],
                               newEntryList[j + 1][0],
                               newEntryList[j][2])
        j += 1
    
    return tier.new(entryList=newEntryList)

     
def intervalOverlapCheck(interval, cmprInterval, percentThreshold=0,
                         timeThreshold=0, boundaryInclusive=False):
    '''
    Checks whether two intervals overlap
    
    If percentThreshold is greater than 0, then if the intervals overlap, they
        must overlap by at least this threshold
    
    If timeThreshold is greater than 0, then if the intervals overlap, they
        must overlap by at least this threshold
        
    If boundaryInclusive is true, then two intervals are considered to overlap
        if they share a boundary
    '''
    
    startTime, endTime = interval[:2]
    cmprStartTime, cmprEndTime = cmprInterval[:2]
    
    overlapTime = max(0, min(endTime, cmprEndTime) -
                      max(startTime, cmprStartTime))
    overlapFlag = overlapTime > 0
    
    # Do they share a boundary?  Only need to check if one boundary ends
    # when another begins (because otherwise, they overlap in other ways)
    boundaryOverlapFlag = False
    if boundaryInclusive:
        boundaryOverlapFlag = (startTime == cmprEndTime or
                               endTime == cmprStartTime)
    
    # Is the overlap over a certain percent?
    percentOverlapFlag = False
    if percentThreshold > 0 and overlapFlag:
        totalTime = max(endTime, cmprEndTime) - min(startTime, cmprStartTime)
        percentOverlap = overlapTime / float(totalTime)
        
        percentOverlapFlag = percentOverlap >= percentThreshold
    
    # Is the overlap more than a certain threshold?
    timeOverlapFlag = False
    if timeThreshold > 0 and overlapFlag:
        timeOverlapFlag = overlapTime > timeThreshold
        
    overlapFlag = (overlapFlag or boundaryOverlapFlag or
                   percentOverlapFlag or timeOverlapFlag)
    
    return overlapFlag


class TextgridCollisionException(Exception):
    
    def __init__(self, tierName, insertInterval, collisionList):
        super(TextgridCollisionException, self).__init__()
        self.tierName = tierName
        self.insertInterval = insertInterval
        self.collisionList = collisionList
        
    def __str__(self):
        dataTuple = (str(self.insertInterval),
                     self.tierName,
                     str(self.collisionList))
        return ("Attempted to insert interval %s into tier %s of textgrid" +
                "but overlapping entries %s already exist" % dataTuple)

    
class TimelessTextgridTierException(Exception):
    
    def __str__(self):
        return "All textgrid tiers much have a min and max duration"


class BadIntervalError(Exception):
    
    def __init__(self, start, stop, label):
        super(BadIntervalError, self).__init__()
        self.start = start
        self.stop = stop
        self.label = label
        
    def __str__(self):
        dataTuple = (self.start, self.stop, self.label)
        return ("Problem with interval--could not create textgrid " +
                "(%s,%s,%s)" % dataTuple)
        

class TextgridTier(object):
    
    tierType = None
    
    def __init__(self, name, entryList, minT, maxT):
        '''See PointTier or IntervalTier'''
        entryList.sort()
        
        self.name = name
        self.entryList = entryList
        self.minTimestamp = minT
        self.maxTimestamp = maxT
    
    def __eq__(self, other):
        def isclose(a, b, rel_tol=1e-14, abs_tol=0.0):
            return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
        
        isEqual = True
        isEqual &= self.name == other.name
        isEqual &= self.minTimestamp == other.minTimestamp
        isEqual &= self.maxTimestamp == other.maxTimestamp
        isEqual &= len(self.entryList) == len(self.entryList)
        
        if isEqual:
            for selfEntry, otherEntry in zip(self.entryList, other.entryList):
                for selfSubEntry, otherSubEntry in zip(selfEntry, otherEntry):
                    try:
                        isEqual &= isclose(selfSubEntry, otherSubEntry)
                    except TypeError:
                        isEqual &= selfSubEntry == otherSubEntry
        
        return isEqual
    
    def appendTier(self, tier):
        
        minTime = self.minTimestamp
        if tier.minTimestamp < minTime:
            minTime = tier.minTimestamp
        
        maxTime = self.maxTimestamp + tier.maxTimestamp
        
        appendTier = tier.editTimestamps(self.maxTimestamp,
                                         allowOvershoot=True)
        
        assert(self.tierType == tier.tierType)
        
        entryList = self.entryList + appendTier.entryList
        entryList.sort()
        
        return self.new(self.name,
                        entryList,
                        minTimestamp=minTime,
                        maxTimestamp=maxTime)

    def deleteEntry(self, entry):
        '''Removes an entry from the entryList'''
        self.entryList.pop(self.entryList.index(entry))
    
    def find(self, matchLabel, substrMatchFlag=False, usingRE=False):
        '''
        Returns the index of all intervals that match the given label
        
        substrMatchFlag: if True, match any label containing matchLabel.
                         if False, label must be the same as matchLabel.
        usingRE: if True, matchLabel is interpreted as a regular expression
        '''
        returnList = []
        if usingRE is True:
            for i, entry in enumerate(self.entryList):
                matchList = re.findall(matchLabel, entry[-1], re.I)
                if matchList != []:
                    returnList.append(i)
        else:
            for i, entry in enumerate(self.entryList):
                if not substrMatchFlag:
                    if entry[-1] == matchLabel:
                        returnList.append(i)
                else:
                    if matchLabel in entry[-1]:
                        returnList.append(i)
        
        return returnList
    
    def getAsText(self):
        '''Prints each entry in the tier on a separate line w/ timing info'''
        text = ""
        text += '"%s"\n' % self.tierType
        text += '"%s"\n' % self.name
        text += '%s\n%s\n%s\n' % (repr(self.minTimestamp),
                                  repr(self.maxTimestamp),
                                  len(self.entryList))
        
        for entry in self.entryList:
            entry = [repr(val) for val in entry[:-1]] + ['"%s"' % entry[-1], ]
            try:
                unicode
            except NameError:
                unicodeFunc = str
            else:
                unicodeFunc = unicode
            
            text += "\n".join([unicodeFunc(val) for val in entry]) + "\n"
            
        return text
    
    def new(self, name=None, entryList=None, minTimestamp=None,
            maxTimestamp=None, pairedWav=None):
        '''Make a new tier derived from the current one'''
        if name is None:
            name = self.name
        if entryList is None:
            entryList = copy.deepcopy(self.entryList)
        if minTimestamp is None:
            minTimestamp = self.minTimestamp
        if maxTimestamp is None and pairedWav is None:
            maxTimestamp = self.maxTimestamp
        return type(self)(name, entryList, minTimestamp, maxTimestamp,
                          pairedWav)
    
    def sort(self):
        '''Sorts the entries in the entryList'''
        # A list containing tuples and lists will be sorted with tuples
        # first and then lists.  To correctly sort, we need to make
        # sure that all data structures inside the entry list are
        # of the same data type.  The entry list is sorted whenever
        # the entry list is modified, so this is probably the best
        # place to enforce the data type
        self.entryList = [tuple(entry) for entry in self.entryList]
        self.entryList.sort()
        
    def union(self, tier):
        '''
        The given tier is set unioned to this tier.
        
        All entries in the given tier are added to the current tier.
        Overlapping entries are merged.
        '''
        retTier = self.new()
        
        for entry in tier.entryList:
            retTier.insertEntry(entry, False, collisionCode='merge')
        
        retTier.sort()
        
        return retTier
        

class PointTier(TextgridTier):
    
    tierType = POINT_TIER
    
    def __init__(self, name, entryList, minT=None, maxT=None,
                 pairedWav=None):
        '''
        A point tier is for annotating instaneous events
        
        The entryList is of the form:
        [(timeVal1, label1), (timeVal2, label2), ]
        
        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('peak point here') or numerical data e.g. (pitch values
        like '132'))
        '''
        
        entryList = [(float(time), label) for time, label in entryList]
        
        # Determine the min and max timestamps
        timeList = [time for time, label in entryList]
        if minT is not None:
            timeList.append(float(minT))
        if maxT is not None:
            timeList.append(float(maxT))
            
        if maxT is None and pairedWav is not None:
            maxT = _getWavDuration(pairedWav)
        
        try:
            minT = min(timeList)
            maxT = max(timeList)
        except ValueError:
            raise TimelessTextgridTierException()

        super(PointTier, self).__init__(name, entryList, minT, maxT)

    def crop(self, cropStart, cropEnd, mode=None,
             rebaseToZero=True):
        '''
        Creates a new tier containing all entries inside the new interval
        
        mode is ignored.  This parameter is kept for compatibility with
        IntervalTier.crop()
        '''
        newEntryList = []
        
        for entry in self.entryList:
            timestamp = entry[0]
            
            if timestamp >= cropStart and timestamp <= cropEnd:
                newEntryList.append(entry)

        if rebaseToZero is True:
            newEntryList = [(timeV - cropStart, label)
                            for timeV, label in newEntryList]
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        # Create subtier
        subTier = PointTier(self.name, newEntryList, minT, maxT)
        return subTier

    def editTimestamps(self, offset, allowOvershoot=False):
        '''
        Modifies all timestamps by a constant amount
        
        If allowOvershoot is True, an interval can go beyond the bounds
        of the textgrid
        '''
        
        newEntryList = []
        for timestamp, label in self.entryList:
            
            newTimestamp = timestamp + offset
            if not allowOvershoot:
                assert(newTimestamp > self.minTimestamp)
                assert(newTimestamp <= self.maxTimestamp)
            
            if newTimestamp < 0:
                continue
            
            newEntryList.append((newTimestamp, label))
        
        # Determine new min and max timestamps
        newMin = min([float(subList[0]) for subList in newEntryList])
        newMax = max([float(subList[1]) for subList in newEntryList])
        
        if newMin > self.minTimestamp:
            newMin = self.minTimestamp
        
        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp
        
        return PointTier(self.name, newEntryList, newMin, newMax)
    
    def getValuesAtPoints(self, dataTupleList, fuzzyMatching=False):
        '''
        Get the values that occur at points in the point tier
        
        If fuzzyMatching is True, if there is not a feature value
        at a point, the nearest feature value will be taken.
        
        The procedure assumes that all data is ordered in time.
        dataTupleList should be in the form
        [(t1, v1a, v1b, ..), (t2, v2a, v2b, ..), ..]
        
        The procedure makes one pass through dataTupleList and one
        pass through self.entryList.  If the data is not sequentially
        ordered, the incorrect response will be returned.
        '''
        
        i = 0
        retList = []
        
        sortedDataTupleList = dataTupleList.sorted()
        for timestamp, label in self.entryList:
            retTuple = utils.getValueAtTime(timestamp,
                                            sortedDataTupleList,
                                            fuzzyMatching=fuzzyMatching,
                                            startI=i)
            retTime, retVal, i = retTuple
            retList.append((retTime, label, retVal))
    
        return retList
        
    def eraseRegion(self, start, stop, collisionCode=None, doShrink=True):
        '''
        Makes a region in a tier blank (removes all contained entries)
        
        collisionCode: Ignored for the moment (added for compatibility
                       with eraseRegion() for Interval Tiers)
        doShrink: if True, moves leftward by (/stop/ - /start/)
                  all points to the right of /stop/
        '''

        newTier = self.new()
        croppedTier = newTier.crop(start, stop, "truncated", False)
        matchList = croppedTier.entryList
        
        if len(matchList) == 0:
            pass
        else:
            
            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for tmpEntry in matchList[::-1]:
                newTier.deleteEntry(tmpEntry)
                
        if doShrink is True:
            newEntryList = []
            diff = stop - start
            for timestamp, label in newTier.entryList:
                if timestamp < start:
                    newEntryList.append((timestamp, label))
                elif timestamp > stop:
                    newEntryList.append((timestamp - diff, label))
            
            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList,
                                  maxTimestamp=newMax)
                    
        return newTier
                
    def insertEntry(self, entry, warnFlag=True, collisionCode=None):
        '''
        inserts an interval into the tier
        
        collisionCode: in the event that intervals exist in the insertion area,
                        one of three things may happen
        - 'replace' - existing items will be removed
        - 'merge' - inserting item will be fused with existing items
        - None or any other value - TextgridCollisionException is thrown
        
        if warnFlag is True and collisionCode is not None,
        the user is notified of each collision
        '''
        timestamp, label = entry
        
        matchList = []
        i = None
        for i, searchEntry in self.entryList:
            if searchEntry[0] == entry[0]:
                matchList.append(searchEntry)
                break
        
        if len(matchList) == 0:
            self.entryList.append(entry)
            
        elif collisionCode.lower() == "replace":
            self.deleteEntry(self.entryList[i])
            self.entryList.append(entry)
            
        elif collisionCode.lower() == "merge":
            oldEntry = self.entryList[i]
            newEntry = (timestamp, "-".join([oldEntry[-1], label]))
            self.deleteEntry(self.entryList[i])
            self.entryList.append(newEntry)
            
        else:
            raise TextgridCollisionException(self.name, entry, matchList)
            
        self.sort()
        
        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(entry), str(matchList), self.name)))
    
    def insertSpace(self, start, duration, collisionCode=None):
        '''
        Inserts a region into the tier
        
        collisionCode: Ignored for the moment (added for compatibility
                       with insertSpace() for Interval Tiers)
        '''
        
        newEntryList = []
        for entry in self.entryList:
            if entry[0] <= start:
                newEntryList.append(entry)
            elif entry[0] > start:
                newEntryList.append((entry[0] + duration, entry[1]))
                
        newTier = self.new(entryList=newEntryList,
                           maxTimestamp=self.maxTimestamp + duration)
        
        return newTier

        
class IntervalTier(TextgridTier):
    
    tierType = INTERVAL_TIER
    
    def __init__(self, name, entryList, minT=None, maxT=None,
                 pairedWav=None):
        '''
        An interval tier is for annotating events that have duration
        
        The entryList is of the form:
        [(startTime1, endTime1, label1), (startTime2, endTime2, label2), ]
        
        The data stored in the labels can be anything but will
        be interpreted as text by praatio (the label could be descriptive
        text e.g. ('erase this region') or numerical data e.g. (average pitch
        values like '132'))
        '''
        entryList = [(float(start), float(stop), label)
                     for start, stop, label in entryList]
        
        if minT is not None:
            minT = float(minT)
        if maxT is not None:
            maxT = float(maxT)
        
        if maxT is None and pairedWav is not None:
            maxT = _getWavDuration(pairedWav)
        
        # Prevent poorly-formed textgrids from being created
        for entry in entryList:
            if entry[0] >= entry[1]:
                fmtStr = "Anomaly: startTime=%f, stopTime=%f, label=%s"
                print((fmtStr % (entry[0], entry[1], entry[2])))
            assert(entry[0] < entry[1])
        
        # Remove whitespace
        tmpEntryList = []
        for start, stop, label in entryList:
            tmpEntryList.append((start, stop, label.strip()))
        entryList = tmpEntryList
        
        # Determine the minimum and maximum timestampes
        minTimeList = [subList[0] for subList in entryList]
        maxTimeList = [subList[1] for subList in entryList]
        
        if minT is not None:
            minTimeList.append(minT)
        if maxT is not None:
            maxTimeList.append(maxT)

        try:
            minT = min(minTimeList)
            maxT = max(maxTimeList)
        except ValueError:
            raise TimelessTextgridTierException()
        
        super(IntervalTier, self).__init__(name, entryList, minT, maxT)
        
    def crop(self, cropStart, cropEnd, mode, rebaseToZero):
        '''
        Creates a new tier with all entries that fit inside the new interval
        
        mode = {'strict', 'lax', 'truncated'}
            If 'strict', only intervals wholly contained by the crop
                interval will be kept
            If 'lax', partially contained intervals will be kept
            If 'truncated', partially contained intervals will be
                truncated to fit within the crop region.
        
        If rebaseToZero is True, the cropped textgrid values will be
            subtracted by the cropStart
        '''
        
        assert(mode in ['strict', 'lax', 'truncated'])
        
        # Debugging variables
        cutTStart = 0
        cutTWithin = 0
        cutTEnd = 0
        firstIntervalKeptProportion = 0
        lastIntervalKeptProportion = 0
        
        newEntryList = []
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
            
            # If it is only partially contained within the superEntry AND
            # inclusion is 'soft', include it anyways
            elif mode == 'lax' and (intervalStart >= cropStart or
                                    intervalEnd <= cropEnd):
                matchedEntry = entry
            
            # If not strict, include partial tiers on the edges
            # -- regardless, record how much information was lost
            #        - for strict=True, the total time of the cut interval
            #        - for strict=False, the portion of the interval that lies
            #            outside the new interval

            # The current interval stradles the end of the new interval
            elif intervalStart >= cropStart and intervalEnd > cropEnd:
                cutTEnd = intervalEnd - cropEnd
                lastIntervalKeptProportion = ((cropEnd - intervalStart) /
                                              (intervalEnd - intervalStart))

                if mode == "truncated":
                    matchedEntry = (intervalStart, cropEnd, intervalLabel)
                    
                else:
                    cutTWithin += cropEnd - cropStart
            
            # The current interval stradles the start of the new interval
            elif intervalStart < cropStart and intervalEnd <= cropEnd:
                cutTStart = cropStart - intervalStart
                firstIntervalKeptProportion = ((intervalEnd - cropStart) /
                                               (intervalEnd - intervalStart))
                if mode == "truncated":
                    matchedEntry = (cropStart, intervalEnd, intervalLabel)
                else:
                    cutTWithin += cropEnd - cropStart

            # The current interval contains the new interval completely
            elif intervalStart <= cropStart and intervalEnd >= cropEnd:

                if mode == "lax":
                    matchedEntry = entry
                elif mode == "truncated":
                    matchedEntry = (cropStart, cropEnd, intervalLabel)
                else:
                    cutTWithin += cropEnd - cropStart
                        
            if matchedEntry is not None:
                newEntryList.append(matchedEntry)

        if rebaseToZero is True:
            newEntryList = [(startT - cropStart, stopT - cropStart, label)
                            for startT, stopT, label in newEntryList]
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd

        # Create subtier
        croppedTier = IntervalTier(self.name, newEntryList, minT, maxT)
        
        # DEBUG info
#         debugInfo = (subTier, cutTStart, cutTWithin, cutTEnd,
#                      firstIntervalKeptProportion, lastIntervalKeptProportion)
    
        return croppedTier
    
    def difference(self, tier):
        '''
        Takes the set difference of this tier and the given one
        
        Any overlapping portions of entries with entries in this textgrid
        will be removed from the returned tier.
        '''
        retTier = self.new()
        
        for entry in tier.entryList:
            retTier = retTier.eraseRegion(entry[0],
                                          entry[1],
                                          collisionCode='truncate',
                                          doShrink=False)
        
        return retTier

    def editTimestamps(self, offset, allowOvershoot=False):
        '''
        Modifies all timestamps by a constant amount
        
        Can modify the interval start independent of the interval end
        
        If allowOvershoot is True, an interval can go beyond the bounds
        of the textgrid
        '''
        
        newEntryList = []
        for start, stop, label in self.entryList:
            
            newStart = offset + start
            newStop = offset + stop
            if allowOvershoot is not True:
                assert(newStart >= self.minTimestamp)
                assert(newStop <= self.maxTimestamp)
            
            if newStop < 0:
                continue
            if newStart < 0:
                newStart = 0
            
            if newStart < 0:
                continue
            
            newEntryList.append((newStart, newStop, label))

        # Determine new min and max timestamps
        newMin = min([entry[0] for entry in newEntryList])
        newMax = max([entry[1] for entry in newEntryList])
        
        if newMin > self.minTimestamp:
            newMin = self.minTimestamp
        
        if newMax < self.maxTimestamp:
            newMax = self.maxTimestamp
        
        return IntervalTier(self.name, newEntryList, newMin, newMax)

    def eraseRegion(self, start, stop, collisionCode=None, doShrink=True):
        '''
        Makes a region in a tier blank (removes all contained entries)
        
        collisionCode: in the event that intervals exist in the insertion area,
                       one of three things may happen
        - 'truncate' - partially contained entries will have the portion
                       removed that overlaps with the target entry
        - 'categorical' - all entries that overlap, even partially, with the
                          target entry will be completely removed
        - None or any other value - AssertionError is thrown
        
        doShrink: if True, moves leftward by (/stop/ - /start/) amount,
                  each item that occurs after /stop/
        '''
        
        matchList = self.crop(start, stop, 'lax', False).entryList
        newTier = self.new()

        # if the collisionCode is not properly set it isn't clear what to do
        assert(collisionCode == 'truncate' or
               collisionCode == 'categorical')
        
        if len(matchList) == 0:
            pass
        else:
            # Remove all the matches from the entryList
            # Go in reverse order because we're destructively altering
            # the order of the list (messes up index order)
            for tmpEntry in matchList[::-1]:
                newTier.deleteEntry(tmpEntry)
            
            # If we're only truncating, reinsert entries on the left and
            # right edges
            if collisionCode == 'truncate':

                # Check left edge
                if matchList[0][0] < start:
                    newEntry = (matchList[0][0],
                                start,
                                matchList[0][-1])
                    newTier.entryList.append(newEntry)
                    
                # Check right edge
                if matchList[-1][1] > stop:
                    newEntry = (stop,
                                matchList[-1][1],
                                matchList[-1][-1])
                    newTier.entryList.append(newEntry)
        
        if doShrink is True:
            
            diff = stop - start
            newEntryList = []
            for entry in newTier.entryList:
                if entry[1] <= start:
                    newEntryList.append(entry)
                elif entry[0] >= stop:
                    newEntryList.append((entry[0] - diff,
                                         entry[1] - diff,
                                         entry[2]))
            
            # Special case: an interval that spanned the deleted
            # section
            for i in range(0, len(newEntryList) - 1):
                rightEdge = newEntryList[i][1] == start
                leftEdge = newEntryList[i + 1][0] == start
                sameLabel = (newEntryList[i][2] == newEntryList[i + 1][2])
                if rightEdge and leftEdge and sameLabel:
                    newEntry = (newEntryList[i][0],
                                newEntryList[i + 1][1],
                                newEntryList[i][2])
                
                    newEntryList.pop(i + 1)
                    newEntryList.pop(i)
                    newEntryList.insert(i, newEntry)
                    
                    # Only one interval can span the deleted section,
                    # so if we've found it, move on
                    break
            
            newMax = newTier.maxTimestamp - diff
            newTier = newTier.new(entryList=newEntryList,
                                  maxTimestamp=newMax)
            
        return newTier
    
    def getValuesInIntervals(self, dataTupleList):
        '''
        Returns data from dataTupleList contained in labeled intervals
        
        dataTupleList should be of the form:
        [(time1, value1a, value1b,...), (time2, value2a, value2b...), ...]
        '''
        
        returnList = []
        
        for interval in self.entryList:
            intervalDataList = utils.getValuesInInterval(dataTupleList,
                                                         interval[0],
                                                         interval[1])
            returnList.append((interval, intervalDataList))
        
        return returnList
            
    def getNonEntries(self):
        '''
        Returns the regions of the textgrid without labels
        
        This can include unlabeled segments and regions marked as silent.
        '''
        entryList = self.entryList
        invertedEntryList = [(entryList[i][1], entryList[i + 1][0], "")
                             for i in range(len(entryList) - 1)]
        
        # Remove entries that have no duration (ie lie between two entries
        # that share a border)
        invertedEntryList = [entry for entry in invertedEntryList
                             if entry[0] < entry[1]]
        
        if entryList[0][0] > 0:
            invertedEntryList.insert(0, (0, entryList[0][0], ""))
        
        if entryList[-1][1] < self.maxTimestamp:
            invertedEntryList.append((entryList[-1][1], self.maxTimestamp, ""))
            
        return invertedEntryList
    
    def insertEntry(self, entry, warnFlag=True, collisionCode=None):
        '''
        inserts an interval into the tier
        
        collisionCode: in the event that intervals exist in the insertion area,
                        one of three things may happen
        - 'replace' - existing items will be removed
        - 'merge' - inserting item will be fused with existing items
        - None or any other value - TextgridCollisionException is thrown
        
        if warnFlag is True and collisionCode is not None,
        the user is notified of each collision
        '''
        startTime, endTime = entry[:2]
        
        matchList = self.crop(startTime, endTime, 'lax', False).entryList
        
        if len(matchList) == 0:
            self.entryList.append(entry)
            
        elif collisionCode.lower() == "replace":
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            self.entryList.append(entry)
            
        elif collisionCode.lower() == "merge":
            for matchEntry in matchList:
                self.deleteEntry(matchEntry)
            matchList.append(entry)
            matchList.sort()  # By starting time
            
            newEntry = (min([entry[0] for entry in matchList]),
                        max([entry[1] for entry in matchList]),
                        "-".join([entry[2] for entry in matchList]))
            self.entryList.append(newEntry)
            
        else:
            raise TextgridCollisionException(self.name, entry, matchList)
            
        self.sort()
        
        if len(matchList) != 0 and warnFlag is True:
            fmtStr = "Collision warning for %s with items %s of tier %s"
            print((fmtStr % (str(entry), str(matchList), self.name)))
    
    def insertSpace(self, start, duration, collisionCode=None):
        '''
        Inserts a blank region into the tier
        
        collisionCode: in the event that an interval stradles the
                       starting point
        - 'stretch' - stretches the interval by /duration/ amount
        - 'split' - splits the interval into two--everything to the
                    right of 'start' will be advanced by 'duration' seconds
        - 'no change' - leaves the interval as is with no change
        - None or any other value - AssertionError is thrown
        '''
        
        # if the collisionCode is not properly set it isn't clear what to do
        assert(collisionCode == 'stretch' or
               collisionCode == 'split' or
               collisionCode == 'no change')
        
        newEntryList = []
        for entry in self.entryList:
            # Entry exists before the insertion point
            if entry[1] <= start:
                newEntryList.append(entry)
            # Entry exists after the insertion point
            elif entry[0] >= start:
                newEntryList.append((entry[0] + duration,
                                     entry[1] + duration,
                                     entry[2]))
            # Entry straddles the insertion point
            elif entry[0] <= start and entry[1] > start:
                if collisionCode == 'stretch':
                    newEntryList.append((entry[0],
                                         entry[1] + duration,
                                         entry[2]))
                elif collisionCode == 'split':
                    # Left side of the split
                    newEntryList.append((entry[0],
                                        start,
                                        entry[2]))
                    # Right side of the split
                    newEntryList.append((start + duration,
                                         start + duration + (entry[1] - start),
                                         entry[2]))
                elif collisionCode == 'no change':
                    newEntryList.append(entry)
        
        newTier = self.new(entryList=newEntryList,
                           maxTimestamp=self.maxTimestamp + duration)
                    
        return newTier
       
    def intersection(self, tier):
        '''
        Takes the set intersection of this tier and the given one
        
        Only intervals that exist in both tiers will remain in the
        returned tier.  If intervals partially overlap, only the overlapping
        portion will be returned.
        '''
        retEntryList = []
        for start, stop, label in tier.entryList:
            subTier = self.crop(start, stop, "truncated", False)
            
            # Combine the labels in the two tiers
            stub = "%s-%%s" % label
            subEntryList = [(subEntry[0], subEntry[1], stub % subEntry[2])
                            for subEntry in subTier.entryList]
            
            retEntryList.extend(subEntryList)
        
        newName = "%s-%s" % (self.name, tier.name)
        
        retTier = self.new(newName, retEntryList)
        
        return retTier

    def morph(self, targetTier, filterFunc=None):
        '''
        Morphs the duration of segments in this tier to those in another
        
        This preserves the labels and the duration of silence in
        this tier while changing the duration of labeled segments.
        '''
        cumulativeAdjustAmount = 0
        lastFromEnd = 0
        newEntryList = []
        for fromEntry, targetEntry in zip(self.entryList,
                                          targetTier.entryList):
            
            fromStart, fromEnd, fromLabel = fromEntry
            targetStart, targetEnd = targetEntry[:2]
            
            # fromStart - lastFromEnd -> was this interval and the
            # last one adjacent?
            toStart = (fromStart - lastFromEnd) + cumulativeAdjustAmount

            currAdjustAmount = (fromEnd - fromStart)
            if filterFunc is None or filterFunc(fromLabel):
                currAdjustAmount = (targetEnd - targetStart)
            
            toEnd = cumulativeAdjustAmount = toStart + currAdjustAmount
            newEntryList.append((toStart, toEnd, fromLabel))
            
            lastFromEnd = fromEnd
            
        newMin = self.minTimestamp
        cumulativeDifference = (newEntryList[-1][1] - self.entryList[-1][1])
        newMax = self.maxTimestamp + cumulativeDifference
            
        return IntervalTier(self.name, newEntryList, newMin, newMax)

        
class Textgrid():
    
    def __init__(self):
        'A container that stores and operates over interval and point tiers'
        self.tierNameList = []  # Preserves the order of the tiers
        self.tierDict = {}
    
        self.minTimestamp = None
        self.maxTimestamp = None
    
    def __eq__(self, other):
        isEqual = True
        isEqual &= self.minTimestamp == other.minTimestamp
        isEqual &= self.maxTimestamp == other.maxTimestamp

        isEqual &= self.tierNameList == other.tierNameList
        if isEqual:
            for tierName in self.tierNameList:
                isEqual &= self.tierDict[tierName] == other.tierDict[tierName]
        
        return isEqual
    
    def addTier(self, tier, tierIndex=None):
        
        if tierIndex is None:
            self.tierNameList.append(tier.name)
        else:
            self.tierNameList.insert(tierIndex, tier.name)
            
        assert(tier.name not in list(self.tierDict.keys()))
        self.tierDict[tier.name] = tier
        
        minV = tier.minTimestamp
        if self.minTimestamp is None or minV < self.minTimestamp:
            self.minTimestamp = minV
        
        maxV = tier.maxTimestamp
        if self.maxTimestamp is None or maxV > self.maxTimestamp:
            self.maxTimestamp = maxV
    
    def appendTextgrid(self, tg, onlyMatchingNames=True):
        '''
        Append one textgrid to the end of this one
        
        if onlyMatchingNames is False, tiers that don't appear in both
        textgrids will also appear
        '''
        retTG = Textgrid()
        
        minTime = self.minTimestamp
        maxTime = self.maxTimestamp + tg.maxTimestamp
        
        # Get all tier names.  Ordered first by this textgrid and
        # then by the other textgrid.
        combinedTierNameList = self.tierNameList
        for tierName in tg.tierNameList:
            if tierName not in combinedTierNameList:
                combinedTierNameList.append(tierName)
        
        # Determine the tier names that will be in the final textgrid
        finalTierNameList = []
        if onlyMatchingNames is False:
            finalTierNameList = combinedTierNameList
        else:
            for tierName in combinedTierNameList:
                if tierName in self.tierNameList:
                    if tierName in tg.tierNameList:
                        finalTierNameList.append(tierName)
        
        # Add tiers from this textgrid
        for tierName in self.tierNameList:
            if tierName in finalTierNameList:
                tier = self.tierDict[tierName]
                retTG.addTier(tier)
        
        # Add tiers from the given textgrid
        for tierName in tg.tierNameList:
            if tierName in finalTierNameList:
                appendTier = tg.tierDict[tierName]
                appendTier = appendTier.new(minTimestamp=minTime,
                                            maxTimestamp=maxTime)
                
                appendTier = appendTier.editTimestamps(self.maxTimestamp)
                
                if tierName in retTG.tierNameList:
                    tier = retTG.tierDict[tierName]
                    newEntryList = retTG.tierDict[tierName].entryList
                    newEntryList += appendTier.entryList
                    
                    tier = tier.new(entryList=newEntryList,
                                    minTimestamp=minTime,
                                    maxTimestamp=maxTime)
                    retTG.replaceTier(tierName, tier)
                    
                else:
                    tier = appendTier
                    tier = tier.new(minTimestamp=minTime,
                                    maxTimestamp=maxTime)
                    retTG.addTier(tier)
        
        return retTG

    def crop(self, cropStart, cropEnd, mode, rebaseToZero):
        '''
        Creates a textgrid where all intervals fit within the crop region
        
        mode = {'strict', 'lax', 'truncated'}
            If 'strict', only intervals wholly contained by the crop
                interval will be kept
            If 'lax', partially contained intervals will be kept
            If 'truncated', partially contained intervals will be
                truncated to fit within the crop region.
            
        If rebaseToZero is True, the cropped textgrid values will be
            subtracted by the cropStart
        '''
        
        assert(mode in ['strict', 'lax', 'truncated'])
        
        newTG = Textgrid()
        
        if rebaseToZero is True:
            minT = 0
            maxT = cropEnd - cropStart
        else:
            minT = cropStart
            maxT = cropEnd
        newTG.minTimestamp = minT
        newTG.maxTimestamp = maxT
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            newTier = tier.crop(cropStart, cropEnd, mode, rebaseToZero)
            newTG.addTier(newTier)
        
        return newTG
    
    def eraseRegion(self, start, stop, doShrink=True):
        '''
        Makes a region in a tier blank (removes all contained entries)
        
        If 'doShrink' is True, all entries appearing after the erased interval
        will be shifted to fill the void (ie the duration of the textgrid
        will be reduced by start - stop)
        '''

        diff = stop - start

        maxTimestamp = self.maxTimestamp
        if doShrink is True:
            maxTimestamp -= diff
        
        newTG = Textgrid()
        for name in self.tierNameList:
            tier = self.tierDict[name]
            tier = tier.eraseRegion(start, stop, 'truncate', doShrink)
            newTG.addTier(tier)

        return newTG
            
    def editTimestamps(self, offset, allowOvershoot=False):
        '''
        Modifies all timestamps by a constant amount
        '''
        
        tg = Textgrid()
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            if len(tier.entryList) > 0:
                tier = tier.editTimestamps(offset, allowOvershoot)
            
            tg.addTier(tier)
        
        return tg
    
    def insertSpace(self, start, duration, collisionCode=None):
        '''
        Inserts a blank region into a textgrid
        
        Every item that occurs after /start/ will be pushed back by
        /duration/ seconds
        
        collisionCode: in the event that an interval stradles the
                       starting point
        - 'stretch' - stretches the interval by /duration/ amount
        - 'split' - splits the interval into two--everything to the
                    right of 'start' will be advanced by 'duration' seconds
        - 'no change' - leaves the interval as is with no change
        - None or any other value - AssertionError is thrown
        '''
        
        newTG = Textgrid()
        newTG.minTimestamp = 0
        newTG.maxTimestamp = self.maxTimestamp + duration
        
        for tierName in self.tierNameList:
            tier = self.tierDict[tierName]
            newTier = tier.insertSpace(start, duration, collisionCode)
            newTG.addTier(newTier)
        
        return newTG

    def mergeTiers(self, includeFunc=None,
                   tierList=None, preserveOtherTiers=True):
        '''
        Combine tiers
        
        /includeFunc/ regulates which intervals to include in the merging
          with all others being tossed (default accepts all)
          
        If /tierList/ is none, combine all tiers.
        '''
        
        if tierList is None:
            tierList = self.tierNameList
            
        if includeFunc is None:
            includeFunc = lambda entryList: True
           
        # Determine the tiers to merge
        intervalTierNameList = []
        pointTierNameList = []
        for tierName in tierList:
            tier = self.tierDict[tierName]
            if isinstance(tier, IntervalTier):
                intervalTierNameList.append(tierName)
            elif isinstance(tier, PointTier):
                pointTierNameList.append(tierName)
        
        # Merge the interval tiers
        intervalTier = None
        if len(intervalTierNameList) > 0:
            intervalTier = self.tierDict[intervalTierNameList.pop(0)]
        for tierName in intervalTierNameList:
            intervalTier = intervalTier.union(self.tierDict[tierName])

        # Merge the point tiers
        pointTier = None
        if len(pointTierNameList) > 0:
            pointTier = self.tierDict[pointTierNameList.pop(0)]
        for tierName in pointTierNameList:
            pointTier = pointTier.merge(self.tierDict[tierName])
        
        # Create the final textgrid to output
        tg = Textgrid()
        
        if intervalTier is not None:
            tg.addTier(intervalTier)
        
        if pointTier is not None:
            tg.addTier(pointTier)
        
        return tg

    def new(self):
        '''Returns a copy of this Textgrid'''
        return copy.deepcopy(self)

    def renameTier(self, oldName, newName):
        oldTier = self.tierDict[oldName]
        tierIndex = self.tierNameList.index(oldName)
        self.removeTier(oldName)
        self.addTier(oldTier.new(newName, oldTier.entryList), tierIndex)
    
    def removeTier(self, name):
        self.tierNameList.pop(self.tierNameList.index(name))
        return self.tierDict.pop(name)

    def replaceTier(self, name, newTier):
        tierIndex = self.tierNameList.index(name)
        self.removeTier(name)
        self.addTier(newTier, tierIndex)
            
    def save(self, fn, minimumIntervalLength=MIN_INTERVAL_LENGTH):
        
        for tier in self.tierDict.values():
            tier.sort()
        
        # Fill in the blank spaces for interval tiers
        for name in self.tierNameList:
            tier = self.tierDict[name]
            if isinstance(tier, IntervalTier):
                
                tier = _fillInBlanks(tier,
                                     "",
                                     self.minTimestamp,
                                     self.maxTimestamp)
                if minimumIntervalLength is not None:
                    tier = _removeUltrashortIntervals(tier,
                                                      minimumIntervalLength)
                self.tierDict[name] = tier
        
        for tier in self.tierDict.values():
            tier.sort()
        
        # Header
        outputTxt = ""
        outputTxt += 'File type = "ooTextFile short"\n'
        outputTxt += 'Object class = "TextGrid"\n\n'
        outputTxt += "%s\n%s\n" % (repr(self.minTimestamp),
                                   repr(self.maxTimestamp))
        outputTxt += "<exists>\n%d\n" % len(self.tierNameList)
        
        for tierName in self.tierNameList:
            outputTxt += self.tierDict[tierName].getAsText()
        
        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(outputTxt)


def openTextgrid(fnFullPath):
    
    try:
        with io.open(fnFullPath, "r", encoding="utf-16") as fd:
            data = fd.read()
    except UnicodeError:
        with io.open(fnFullPath, "r", encoding="utf-8") as fd:
            data = fd.read()
    data = data.replace("\r\n", "\n")
    
    caseA = "ooTextFile short" in data
    caseB = "item [" not in data
    if caseA or caseB:
        textgrid = _parseShortTextgrid(data)
    else:
        textgrid = _parseNormalTextgrid(data)
    
    return textgrid


def _parseNormalTextgrid(data):
    '''
    Reads a normal textgrid
    '''
    newTG = Textgrid()
    
    # Toss textgrid header
    header, data = data.split("item [", 1)
    
    headerList = header.split("\n")
    tgMin = float(headerList[3].split("=")[1].strip())
    tgMax = float(headerList[4].split("=")[1].strip())
    
    newTG.minTimestamp = tgMin
    newTG.maxTimestamp = tgMax
    
    # Process each tier individually (will be output to separate folders)
    tierList = data.split("item [")[1:]
    for tierTxt in tierList:
        
        if 'class = "IntervalTier"' in tierTxt:
            tierType = INTERVAL_TIER
            searchWord = "intervals ["
        else:
            tierType = POINT_TIER
            searchWord = "points ["
        
        # Get tier meta-information
        header, tierData = tierTxt.split(searchWord, 1)
        tierName = header.split("name = ")[1].split("\n", 1)[0]
        tierStart = header.split("xmin = ")[1].split("\n", 1)[0]
        tierStart = strToIntOrFloat(tierStart)
        tierEnd = header.split("xmax = ")[1].split("\n", 1)[0]
        tierEnd = strToIntOrFloat(tierEnd)
        tierName = tierName.strip()[1:-1]
        
        # Get the tier entry list
        tierEntryList = []
        labelI = 0
        if tierType == INTERVAL_TIER:
            while True:
                try:
                    timeStart, timeStartI = _fetchRow(tierData,
                                                      "xmin = ", labelI)
                    timeEnd, timeEndI = _fetchRow(tierData,
                                                  "xmax = ", timeStartI)
                    label, labelI = _fetchRow(tierData, "text =", timeEndI)
                except (ValueError, IndexError):
                    break
                
                label = label.strip()
                if label == "":
                    continue
                tierEntryList.append((timeStart, timeEnd, label))
            tier = IntervalTier(tierName, tierEntryList, tierStart, tierEnd)
        else:
            header, tierData = tierTxt.split("points [", 1)
            while True:
                try:
                    time, timeI = _fetchRow(tierData, "number = ", labelI)
                    label, labelI = _fetchRow(tierData, "mark =", timeI)
                except (ValueError, IndexError):
                    break
                
                label = label.strip()
                if label == "":
                    continue
                tierEntryList.append((time, label))
            tier = PointTier(tierName, tierEntryList, tierStart, tierEnd)
        
        newTG.addTier(tier)
        
    return newTG


def _parseShortTextgrid(data):
    '''
    Reads a short textgrid file
    '''
    newTG = Textgrid()
    
    intervalIndicies = [(i, True)
                        for i in utils.findAll(data, '"IntervalTier"')]
    pointIndicies = [(i, False) for i in utils.findAll(data, '"TextTier"')]
    
    indexList = intervalIndicies + pointIndicies
    indexList.append((len(data), None))  # The 'end' of the file
    indexList.sort()
    
    tupleList = [(indexList[i][0], indexList[i + 1][0], indexList[i][1])
                 for i in range(len(indexList) - 1)]
    
    # Set the textgrid's min and max times
    header = data[:tupleList[0][0]]
    headerList = header.split("\n")
    tgMin = float(headerList[3].strip())
    tgMax = float(headerList[4].strip())
    
    newTG.minTimestamp = tgMin
    newTG.maxTimestamp = tgMax

    # Load the data for each tier
    for blockStartI, blockEndI, isInterval in tupleList:
        tierData = data[blockStartI:blockEndI]
        
        # First row contains the tier type, which we already know
        metaStartI = _fetchRow(tierData, '', 0)[1]
        
        # Tier meta-information
        tierName, tierNameEndI = _fetchRow(tierData, '', metaStartI)
        tierStartTime, tierStartTimeI = _fetchRow(tierData, '', tierNameEndI)
        tierEndTime, tierEndTimeI = _fetchRow(tierData, '', tierStartTimeI)
        startTimeI = _fetchRow(tierData, '', tierEndTimeI)[1]
        
        tierStartTime = strToIntOrFloat(tierStartTime)
        tierEndTime = strToIntOrFloat(tierEndTime)
        
        # Tier entry data
        entryList = []
        if isInterval:
            while True:
                try:
                    startTime, endTimeI = _fetchRow(tierData, '', startTimeI)
                    endTime, labelI = _fetchRow(tierData, '', endTimeI)
                    label, startTimeI = _fetchRow(tierData, '', labelI)
                except (ValueError, IndexError):
                    break
                
                label = label.strip()
                if label == "":
                    continue
                entryList.append((startTime, endTime, label))
                
            newTG.addTier(IntervalTier(tierName, entryList,
                                       tierStartTime, tierEndTime))
            
        else:
            while True:
                try:
                    time, labelI = _fetchRow(tierData, '', startTimeI)
                    label, startTimeI = _fetchRow(tierData, '', labelI)
                except (ValueError, IndexError):
                    break
                label = label.strip()
                if label == "":
                    continue
                entryList.append((time, label))
                
            newTG.addTier(PointTier(tierName, entryList,
                                    tierStartTime, tierEndTime))

    return newTG


def strToIntOrFloat(inputStr):
    return float(inputStr) if '.' in inputStr else int(inputStr)


def _fetchRow(dataStr, searchStr, index):
    startIndex = dataStr.index(searchStr, index) + len(searchStr)
    endIndex = dataStr.index("\n", startIndex)
    
    word = dataStr[startIndex:endIndex]
    word = word.strip()
    if word[0] == '"' and word[-1] == '"':
        word = word[1:-1]
    word = word.strip()
    
    return word, endIndex + 1
