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


def _shiftTimes(tg, timeV, newTimeV):
    '''
    Change all instances of timeV in the textgrid to newTimeV
    
    These are meant to be small changes.  No checks are done to see
    if the new interval steps on other intervals
    '''
    tg = tg.new()
    for tierName in tg.tierNameList:
        tier = tg.tierDict[tierName]
        
        if isinstance(tier, tgio.IntervalTier):
            entryList = [entry for entry in tier.entryList
                         if entry[0] == timeV or entry[1] == timeV]
            insertEntryList = []
            for entry in entryList:
                if entry[0] == timeV:
                    newStart, newStop = newTimeV, entry[1]
                elif entry[1] == timeV:
                    newStart, newStop = entry[0], newTimeV
                tier.deleteEntry(entry)
                insertEntryList.append((newStart, newStop, entry[2]))
            
            for entry in insertEntryList:
                tier.insertEntry(entry)
        
        elif isinstance(tier, tgio.PointTier):
            entryList = [entry for entry in tier.entryList
                         if entry[0] == timeV]
            for entry in entryList:
                tier.deleteEntry(entry)
                tier.insertEntry((newTimeV, entry[1]))
    
    return tg


def audioSplice(audioObj, spliceSegment, tg, tierName, newLabel,
                insertStart, insertStop=None, alignToZeroCrossing=True):
    '''
    Splices a segment into an audio file and corresponding textgrid
    
    audioObj - the audio to splice into
    spliceSegment - the audio segment that will be placed into a larger audio
                    file
    tg - the textgrid to splice into
    tierName - the tier that will receive the new label
    newLabel - the label for the splice interval on the tier with name tierName
    insertStart - the time to insert the splice
    insertStop - if not None, will erase the region between sourceSpStart
                 and sourceSpEnd.  (In practice this means audioSplice
                 removes one segment and inserts another in its place)
    alignToZeroCrossing - if True, moves all involved times to the nearest
                          zero crossing in the audio.  Generally results
                          in better sounding output
    '''

    retTG = tg.new()

    # Ensure all time points involved in splicing fall on zero crossings
    if alignToZeroCrossing is True:
        
        # Cut the splice segment to zero crossings
        spliceDuration = spliceSegment.getDuration()
        spliceZeroStart = spliceSegment.findNearestZeroCrossing(0)
        spliceZeroEnd = spliceSegment.findNearestZeroCrossing(spliceDuration)
        spliceSegment = spliceSegment.getSubsegment(spliceZeroStart,
                                                    spliceZeroEnd)
            
        # Move the textgrid borders to zero crossings
        oldInsertStart = insertStart
        insertStart = audioObj.findNearestZeroCrossing(oldInsertStart)
        retTG = _shiftTimes(retTG, oldInsertStart, insertStart)
        
        if insertStop is not None:
            oldInsertStop = insertStop
            insertStop = audioObj.findNearestZeroCrossing(oldInsertStop)
            retTG = _shiftTimes(retTG, oldInsertStop, insertStop)
    
    # Get the start time
    insertTime = insertStart
    if insertStop is not None:
        insertTime = insertStop
    
    # Insert into the audio file
    audioObj.insert(insertTime, spliceSegment.audioSamples)
    
    # Insert a blank region into the textgrid on all tiers
    targetDuration = spliceSegment.getDuration()
    retTG = retTG.insertSpace(insertTime, targetDuration, 'stretch')
    
    # Insert the splice entry into the target tier
    newEntry = (insertTime, insertTime + targetDuration, newLabel)
    retTG.tierDict[tierName].insertEntry(newEntry)
    
    # Finally, delete the old section if requested
    if insertStop is not None:
        audioObj.deleteSegment(insertStart, insertStop)
        retTG = retTG.eraseRegion(insertStart, insertStop, doShrink=True)
        
    return audioObj, retTG
        
    
def spellCheckEntries(tg, targetTierName, newTierName, checkFunction,
                      printEntries=False):
    '''
    Spell checks words in a textgrid
    
    Entries can contain one or more words, separated by whitespace.
    If a mispelling is found, it is noted in a special tier and optionally
    printed to the screen.
    
    checkFunction is user-defined.  There are robust spell check libraries
    for python like woosh or pyenchant.  I have already written a naive
    spell checker in the pysle.praattools library.
    
    checkFunction: should return True if a word is spelled correctly and
                   False otherwise
    '''
    punctuationList = ['_', ',', "'", '"', '!', '?', '.', ';', ]
    
    tg = tg.new()
    tier = tg.tierDict[targetTierName]
    
    mispelledEntryList = []
    for startT, stopT, label in tier.entryList:
        
        # Remove punctuation
        for char in punctuationList:
            label = label.replace(char, "")
        
        wordList = label.split()
        mispelledList = []
        for word in wordList:
            if not checkFunction(word):
                mispelledList.append(word)
        
        if len(mispelledList) > 0:
            mispelledTxt = u", ".join(mispelledList)
            mispelledEntryList.append((startT, stopT, mispelledTxt))
            
            if printEntries is True:
                print((startT, stopT, mispelledTxt))
    
    tier = tgio.IntervalTier(newTierName, mispelledEntryList,
                             tg.minTimestamp, tg.maxTimestamp)
    tg.addTier(tier)
    
    return tg


def splitTierEntries(tg, sourceTierName, targetTierName,
                     startT=None, endT=None):
    '''
    Split each entry in a tier by space
    
    The split entries will be placed on a new tier.  The split entries
    are equally allocated a subsegment of the interval occupied by the
    source tier.  e.g. [(63, 66, 'the blue cat'), ] would become
    [(63, 64, 'the'), (64, 65, 'blue'), (65, 66, 'cat'), ]
    
    This could be used to decompose utterances into words or, with pysle,
    words into phones.
    '''
    minT = tg.minTimestamp
    maxT = tg.maxTimestamp
    
    sourceTier = tg.tierDict[sourceTierName]
    targetTier = None
    
    # Examine a subset of the source tier?
    if startT is not None or endT is not None:
        if startT is None:
            startT = minT
        if endT is None:
            endT = maxT
        
        sourceTier = sourceTier.crop(startT, endT, "truncated", False)
        
        if targetTierName in tg.tierNameList:
            targetTier = tg.tierDict[targetTierName]
            targetTier = targetTier.eraseRegion(startT, endT,
                                                'truncate', False)
    
    # Split the entries in the source tier
    newEntryList = []
    for start, stop, label in sourceTier.entryList:
        labelList = label.split()
        intervalLength = (stop - start) / float(len(labelList))
        
        newSubEntryList = [(start + intervalLength * i,
                            start + intervalLength * (i + 1),
                            label)
                           for i, label in enumerate(labelList)]
        newEntryList.extend(newSubEntryList)
    
    # Create a new tier
    if targetTier is None:
        targetTier = tgio.IntervalTier(targetTierName, newEntryList,
                                       minT, maxT)
    
    # Or insert new entries into existing target tier
    else:

        for entry in newEntryList:
            targetTier.insertEntry(entry, True)
    
    # Insert the tier into the textgrid
    if targetTierName in tg.tierNameList:
        tg.removeTier(targetTierName)
    tg.addTier(targetTier)
    
    return tg
    
    
def tgBoundariesToZeroCrossings(tg, wavObj, adjustPointTiers=True):
    '''
    Makes all textgrid interval boundaries fall on pressure wave zero crossings
    
    adjustPointTiers: if True, point tiers will be adjusted too.  Otherwise,
                      only interval tiers are adjusted.
    '''
    
    for tierName in tg.tierNameList[:]:
        tier = tg.tierDict[tierName]
        
        newEntryList = []
        if isinstance(tier, tgio.PointTier) and adjustPointTiers is True:
            for start, label in tier.entryList:
                newStart = wavObj.findNearestZeroCrossing(start)
                newEntryList.append((newStart, label))
                
        elif isinstance(tier, tgio.IntervalTier):
            
            for start, stop, label in tier.entryList:
                newStart = wavObj.findNearestZeroCrossing(start)
                newStop = wavObj.findNearestZeroCrossing(stop)
                newEntryList.append((newStart, newStop, label))
        
        newTier = tier.new(entryList=newEntryList)
        tg.replaceTier(tierName, newTier)
                
    return tg


def splitAudioOnTier(wavFN, tgFN, tierName, outputPath,
                     outputTGFlag=False, nameStyle=None,
                     noPartialIntervals=False, silenceLabel=None):
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
    silenceLabel: the label for silent regions.  If silences are unlabeled
                  intervals (i.e. blank) then leave this alone.  If silences
                  are labeled using praat's "annotate >> to silences"
                  then this value should be "silences"
    '''
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)
    
    if noPartialIntervals is True:
        mode = 'strict'
    else:
        mode = 'truncated'
    
    tg = tgio.openTextgrid(tgFN)
    entryList = tg.tierDict[tierName].entryList
    
    if silenceLabel is not None:
        entryList = [entry for entry in entryList
                     if entry[2] != silenceLabel]
    
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
    wavQObj = audioio.WavQueryObj(wavFN)
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
        
        frames = wavQObj.getFrames(start, stop)
        wavQObj.outputModifiedWav(frames, outputFNFullPath)
        
        outputFNList.append((start, stop, outputName + ".wav"))
        
        # Output the textgrid if requested
        if outputTGFlag is not False:
            subTG = tg.crop(start, stop, mode, True)
            
            if isinstance(outputTGFlag, str):
                for tierName in subTG.tierNameList:
                    if tierName != outputTGFlag:
                        subTG.removeTier(tierName)
            
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
    tg = tgio.openTextgrid(tgFN)
    
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

    croppedTG = tg.crop(filterStartT, filterStopT, "lax", False)

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
