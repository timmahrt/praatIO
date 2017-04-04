'''
Common/generic scripts or utilities that extend the functionality of
praatio

Created on Jul 27, 2015

@author: tmahrt
'''

import os
from os.path import join
import math
import copy

from praatio import tgio
from praatio import audioio


def tgBoundariesToZeroCrossings(tgFN, wavFN, outputTGFN, adjustPoints=True):
    '''
    Makes all textgrid interval boundaries fall on pressure wave zero crossings
    
    maxShiftAmount specifies the search space in seconds (the amount before and
        after the given time)
    if ignoreOnFailure is true, a warning is printed to the screen and
        the given timestamp is returned
    '''
    
    wavQObj = audioio.WavQueryObj(wavFN)
    
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]
        
        newEntryList = []
        if isinstance(tier, tgio.PointTier) and adjustPoints is True:
            for start, label in tier.entryList:
                newStart = wavQObj.findNearestZeroCrossing(start)
                newEntryList.append((newStart, label))
                
        elif isinstance(tier, tgio.IntervalTier):
            
            for start, stop, label in tier.entryList:
                newStart = wavQObj.findNearestZeroCrossing(start)
                newStop = wavQObj.findNearestZeroCrossing(stop)
                newEntryList.append((newStart, newStop, label))
        
        tg.replaceTier(tierName, newEntryList, True)
                
    tg.save(outputTGFN)


def splitAudioOnTier(wavFN, tgFN, tierName, outputPath,
                     outputTGFlag=False, nameStyle=None,
                     noPartialIntervals=False):
    '''
    Outputs one subwav for each entry in the tier of a textgrid
    
    outputTGFlag: If True, outputs paired, cropped textgrids
                  If is type str (a tier name), outputs a paired, cropped
                  textgrid with only the specified tier
    nameStyle: if 'append': append interval label to output name
               if 'append_no_i': append label but not interval to output name
               if 'label': output name is the same as label
               if None: output name plus the interval number
    noPartialIntervals: if True: intervals in non-target tiers that are
                                  not wholly contained by an interval in
                                  the target tier will not be included in
                                  the output textgrids
    '''
    tg = tgio.openTextGrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    # Build the output name template
    name = os.path.splitext(os.path.split(wavFN)[1])[0]
    orderOfMagnitude = int(math.floor(math.log10(len(entryList))))
    
    # We want one more zero in the output than the order of magnitude
    outputTemplate = "%s_%%0%dd" % (name, orderOfMagnitude + 1)
    
    firstWarning = True
    
    # If we're using the 'label' namestyle for outputs, all of the
    # interval labels have to be unique, or wave files with those
    # labels as names, will be overwritten
    if nameStyle == 'label':
        wordList = [word for _, _, word in entryList]
        multipleInstList = []
        for word in set(wordList):
            if wordList.count(word) > 1:
                multipleInstList.append(word)
        
        if len(multipleInstList) > 0:
            instListTxt = "\n".join(multipleInstList)
            print(("Overwriting wave files in: %s\n" +
                   "Intervals exist with the same name:\n%s")
                  % (outputPath, instListTxt))
            firstWarning = False
    
    # Output wave files
    outputFNList = []
    for i, entry in enumerate(entryList):
        start, stop, label = entry
        
        # Resolve output name
        outputName = outputTemplate % i
        if nameStyle == "append":
            outputName += "_" + label
        elif nameStyle == "append_no_i":
            outputName = name + "_" + label
        elif nameStyle == "label":
            outputName = label
        
        outputFNFullPath = join(outputPath, outputName + ".wav")

        if os.path.exists(outputFNFullPath) and firstWarning:
            print(("Overwriting wave files in: %s\n" +
                   "Files existed before or intervals exist with " +
                   "the same name:\n%s")
                  % (outputPath, outputName))
        
        audioObj = audioio.openAudioFile(wavFN,
                                         keepList=[(start, stop), ],
                                         doShrink=True)
        audioObj.save(outputFNFullPath)
        outputFNList.append((start, stop, outputName + ".wav"))
        
        # Output the textgrid if requested
        if outputTGFlag is not False:
            subTG = tg.crop(noPartialIntervals, False, start, stop)
            
            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNameList:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)
        
            # Adjust the new time on the intervals, the textgrid,
            # and the textgrid tiers
            # the crop start time becomes the new '0' value
            offset = -1 * start
            subTG = subTG.editTimestamps(offset, offset, offset)
            subTG.minTimestamp = 0
            subTG.maxTimestamp = stop - start
            for tierName in subTG.tierNameList:
                subTG.tierDict[tierName].minTimestamp = 0
                subTG.tierDict[tierName].maxTimestamp = stop - start
            
            subTG.save(join(outputPath, outputName + ".TextGrid"))
    
    return outputFNList


def alignBoundariesAcrossTiers(tgFN, maxDifference=0.01):
    '''
    Aligns boundaries or points in a textgrid that suffer from 'jitter'
    
    Often times, boundaries in different tiers are meant to line up.
    For example the boundary of the first phone in a word and the start
    of the word.  If manually annotated, however, those values might
    not be the same, even if they were intended to be the same.
    
    This script will force all boundaries within /maxDifference/ amount
    to be the same value.  The replacement value is either the majority
    value found within /maxDifference/ or, if no majority exists, than
    the value used in the search query.
    '''
    tg = tgio.openTextGrid(tgFN)
    
    for tierName in tg.tierNameList:
        altNameList = [tmpName for tmpName in tg.tierNameList
                       if tmpName != tierName]
        
        tier = tg.tierDict[tierName]
        for entry in tier.entryList:
            # Interval tier left boundary or point tier point
            _findMisalignments(tg, entry[0], maxDifference,
                               altNameList, tierName, entry, 0)
        
        # Interval tier right boundary
        if tier.tierType == tgio.INTERVAL_TIER:
            for entry in tier.entryList:
                _findMisalignments(tg, entry[1], maxDifference,
                                   altNameList, tierName, entry, 1)

    return tg

            
def _findMisalignments(tg, timeV, maxDifference, tierNameList,
                       tierName, entry, orderID):
    '''
    This is just used by alignBoundariesAcrossTiers()
    '''
    # Get the start time
    filterStartT = timeV - maxDifference
    if filterStartT < 0:
        filterStartT = 0
    
    # Get the end time
    filterStopT = timeV + maxDifference
    if filterStopT > tg.maxTimestamp:
        filterStopT = tg.maxTimestamp

    croppedTG = tg.crop(False, True, filterStartT, filterStopT)

    matchList = [(tierName, timeV, entry, orderID)]
    for subTierName in tierNameList:
        subCroppedTier = croppedTG.tierDict[subTierName]
        
        # For each item that exists in the search span, find the boundary
        # that lies in the search span
        for subCroppedEntry in subCroppedTier.entryList:
            
            if subCroppedTier.tierType == tgio.INTERVAL_TIER:
                subStart, subEnd, _ = subCroppedEntry
                
                # Left boundary?
                leftMatchVal = None
                if subStart >= filterStartT and subStart <= filterStopT:
                    leftMatchVal = subStart

                # Right boundary?
                rightMatchVal = None
                if subEnd >= filterStartT and subEnd <= filterStopT:
                    rightMatchVal = subEnd
                    
                # There should be at most one matching boundary
                assert(leftMatchVal is None or rightMatchVal is None)
                
                # Set the matching boundary info
                if leftMatchVal is not None:
                    matchVal = leftMatchVal
                    subOrderID = 0
                else:
                    matchVal = rightMatchVal
                    subOrderID = 1
            
                # Match value could be none if, for an interval tier,
                # no boundary sits inside the search span (the search span
                # is wholly inside the interval)
                if matchVal is None:
                    continue
            
            elif subCroppedTier.tierType == tgio.POINT_TIER:
                subStart, _ = subCroppedEntry
                if subStart >= filterStartT and subStart <= filterStopT:
                    matchVal = subStart
                    subOrderID = 0

            matchList.append((subTierName, matchVal, subCroppedEntry,
                              subOrderID))
    
    # Find the number of different values that are almost the same
    valList = [row[1] for row in matchList]
    valUniqueList = []
    for val in valList:
        if val not in valUniqueList:
            valUniqueList.append(val)
            
    # If they're all the same, there is nothing to do
    # If some are different, take the most common value (or else the first
    # one) and set all similar times to that value
    if len(valUniqueList) > 1:
        countList = [valList.count(val) for val in valUniqueList]
        bestVal = valUniqueList[countList.index(max(countList))]
        assert(bestVal is not None)
        for tierName, _, oldEntry, orderID in matchList:

            newEntry = list(copy.deepcopy(oldEntry))
            newEntry[orderID] = bestVal
            newEntry = tuple(newEntry)
        
            tg.tierDict[tierName].deleteEntry(oldEntry)
            tg.tierDict[tierName].entryList.append(newEntry)
            tg.tierDict[tierName].entryList.sort()
