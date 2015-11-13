'''
Functions for reading/writing/manipulating klattgrid files in praat

Created on Oct 30, 2015

@author: tmahrt


For more information on the praat klattgrid:
http://www.fon.hum.uva.nl/praat/manual/KlattGrid.html

There are three kinds of data types in a klattgrid:
null tiers (contain no data points -- seem to function as headers for a
            set of regular tiers)
regular tiers
embedded tiers

In this code:
null tiers and regular tiers are both represented by KlattPointTier

embedded tiers contain tiers of tiers (3 layers)
A KlattContainerTier contains a list of KlattIntermediateTiers which
contains a list of KlattSubPointTiers.  Only the KlattSubPointTiers contain
any points
'''

import codecs

from praatio import common
from praatio import tgio


class _KlaatBaseTier(object):

    def __init__(self, name):
        self.tierNameList = []  # Preserves the order of the tiers
        self.tierDict = {}
        self.name = name
        self.minTimestamp = None
        self.maxTimestamp = None
        
    def addTier(self, tier, tierIndex=None):
        
        if tierIndex is None:
            self.tierNameList.append(tier.name)
        else:
            self.tierNameList.insert(tierIndex, tier.name)
            
        assert(tier.name not in list(self.tierDict.keys()))
        self.tierDict[tier.name] = tier
        
        minV = tier.minTimestamp
        if self.minTimestamp is None or (minV is not None and
                                         minV < self.minTimestamp):
            self.minTimestamp = minV
        
        maxV = tier.maxTimestamp
        if self.maxTimestamp is None or (maxV is not None and
                                         maxV > self.maxTimestamp):
            self.maxTimestamp = maxV


class KlattContainerTier(_KlaatBaseTier):
    '''
    Contains a set of intermediate tiers
    '''
    def getAsText(self):
        outputTxt = ""
        outputTxt += "%s? <exists>\n" % self.name
        
        try:
            outputTxt += "xmin = %s\nxmax = %s\n" % (self.minTimestamp,
                                                     self.maxTimestamp)
        except TypeError:
            pass
        
        for name in self.tierNameList:
            outputTxt += self.tierDict[name].getAsText()
        
        return outputTxt
    
    def modifySubtiers(self, tierName, modFunc):
        '''
        Modify values in every tier contained in the named intermediate tier
        '''
        kit = self.tierDict[tierName]
        for name in kit.tierNameList:
            subpointTier = kit.tierDict[name]
            subpointTier.modifyValues(modFunc)
    
    
class KlattIntermediateTier(_KlaatBaseTier):
    '''
    Has many point tiers that are semantically related (e.g. formant tiers)
    '''
    def getAsText(self):
        outputTxt = ""
        headerTxt = "%s: size=%d\n" % (self.name, len(self.tierNameList))
        
        for name in self.tierNameList:
            outputTxt += self.tierDict[name].getAsText()
        
        outputTxt = headerTxt + outputTxt
        
        return outputTxt


class KlattSubPointTier(tgio.PointTier):
    '''
    Tiers contained in a KlattIntermediateTier
    '''
    def getAsText(self):
        outputList = []
        outputList.append("%s:" % self.name)
        outputList.append("    xmin = %s" % self.minTimestamp)
        outputList.append("    xmax = %s" % self.maxTimestamp)
        outputList.append("    points: size = %d" % len(self.entryList))
        
        for i, entry in enumerate(self.entryList):
            outputList.append("    points [%d]:" % (i + 1))
            outputList.append("        number = %s" % entry[0])
            outputList.append("        value = %s" % entry[1])
    
        return "\n".join(outputList) + '\n'
    

class KlattPointTier(tgio.PointTier):
    '''
    A Klatt tier not contained within another tier
    '''
    def modifyValues(self, modFunc):
        newEntryList = []
        for timestamp, value in self.entryList:
            newEntryList.append((timestamp, modFunc(value)))
        
        self.entryList = newEntryList
        
    def getAsText(self):
        outputList = []
        
        outputList.append("%s? <exists> " % self.name)
        outputList.append("xmin = %s" % self.minTimestamp)
        outputList.append("xmax = %s" % self.maxTimestamp)
        
        if self.name not in ["phonation", "vocalTract", "coupling",
                             "frication"]:
            outputList.append("points: size= %d" % len(self.entryList))
        
        for i, entry in enumerate(self.entryList):
            outputList.append("points [%d]:" % (i + 1))
            outputList.append("    number = %s" % entry[0])
            outputList.append("    value = %s" % entry[1])
    
        return "\n".join(outputList) + "\n"

    
class Klattgrid(tgio.Textgrid):
    
    def save(self, fn):
        
        # Header
        outputTxt = ""
        outputTxt += 'File type = "ooTextFile"\n'
        outputTxt += 'Object class = "KlattGrid"\n\n'
        outputTxt += "xmin = %s\nxmax = %s\n" % (self.minTimestamp,
                                                 self.maxTimestamp)
        
        for tierName in self.tierNameList:
            outputTxt += self.tierDict[tierName].getAsText()
        
        outputTxt = _cleanNumericValues(outputTxt)
        
        codecs.open(fn, "w", encoding="utf-8").write(outputTxt)
    

def openKlattGrid(fnFullPath):

    try:
        data = codecs.open(fnFullPath, "rU", encoding="utf-16").read()
    except UnicodeError:
        data = codecs.open(fnFullPath, "rU", encoding="utf-8").read()
    data = data.replace("\r\n", "\n")

    # Right now, can only open normal klatt grid and not short ones
    kg = _openNormalKlattGrid(data)

    return kg


def _openNormalKlattGrid(data):

    kg = Klattgrid()

    # Toss header
    data = data.split("\n\n", 1)[1]
    
    # Not sure if this is needed
    startI = data.index("points")
    startI = data.index("\n", startI)
    
    # Find sections
    sectionIndexList = _findIndicies(data, "<exists>")
    
    sectionIndexList.append(-1)
    
    for i in xrange(len(sectionIndexList) - 1):
        dataTuple = _getSectionHeader(data, sectionIndexList, i)
        name, minT, maxT, sectionData, sectionTuple = dataTuple
        
        # Container Tier
        if name in ["oral_formants", "nasal_formants", "nasal_antiformants",
                    "tracheal_formants", "tracheal_antiformants",
                    "delta_formants", "frication_formants"]:
            
            kct = _proccessContainerTierInput(sectionData, name)
            kg.addTier(kct)
                    
        else:
        
            # Process entries if this tier has any
            entryList = _buildEntryList(sectionTuple)
            tier = KlattPointTier(name, entryList, minT, maxT)
            kg.addTier(tier)
        
    return kg


def _proccessContainerTierInput(sectionData, name):
    sectionData = sectionData.split("\n", 3)[-1]
    
    formantIndexList = _findIndicies(sectionData, 'formants')
    
    subFilterList = ['bandwidths',
                     "oral_formants_amplitudes",
                     "nasal_formants_amplitudes",
                     "tracheal_formants_amplitudes",
                     "frication_formants_amplitudes"]
    
    # Find the index of all the different data sections
    subFilterIndexList = [_findIndicies(sectionData, subName)
                          for subName in subFilterList]
    
    # 'Formant' search query finds duplicates -- remove them
    newFormantList = []
    for value in formantIndexList:
        if all([value not in subList for subList in subFilterIndexList]):
            newFormantList.append(value)
    formantIndexList = newFormantList

    # Combine regular query with formant query
    indexListOfLists = [formantIndexList, ] + subFilterIndexList
    
    # Flatten index list
    masterIndexList = [value for sublist in indexListOfLists
                       for value in sublist]
    masterIndexList.sort()
    
    # If an index list is last, it it needs to include '-1' to capture the
    # rest of the data
    for subList in indexListOfLists:
        try:
            val = subList[-1]
        except IndexError:
            continue
        ii = masterIndexList.index(val)  # Index of the index
        try:
            subList.append(masterIndexList[ii + 1] - 1)
        except IndexError:
            subList.append(-1)
    
    # Build the tier structure
    kct = KlattContainerTier(name)
    for indexList in indexListOfLists:
        if indexList == []:
            continue
        tierList = []
        for j in xrange(len(indexList) - 1):
            try:
                tmpTuple = _getSectionHeader(sectionData, indexList, j)
            except ValueError:
                continue
            subName, subMin, subMax, _, subTuple = tmpTuple
            subName = subName[:-1]
            
            entryList = _buildEntryList(subTuple)
            tier = KlattSubPointTier(subName, entryList,
                                     subMin, subMax)
            tierList.append(tier)
        kit = KlattIntermediateTier(subName.split()[0])
        for tier in tierList:
            kit.addTier(tier)
        kct.addTier(kit)
    
    return kct


def _findIndicies(data, keyword):
    indexList = common.findAll(data, keyword)
    indexList = [data.rfind("\n", 0, i) for i in indexList]
    
    return indexList


def _getSectionHeader(data, indexList, i):
    sectionStart = indexList[i]
    sectionEnd = indexList[i + 1]
    sectionData = data[sectionStart:sectionEnd].strip()
    sectionTuple = sectionData.split("\n", 4)
    
    subheader, minr, maxr = sectionTuple[:3]
    name = subheader.split("?")[0].strip()
    minT = float(minr.split("=")[1].strip())
    maxT = float(maxr.split("=")[1].strip())

    tail = sectionTuple[3:]

    return name, minT, maxT, sectionData, tail


def _buildEntryList(sectionTuple):
    entryList = []
    if len(sectionTuple) > 1:  # Has points
        npoints = float(sectionTuple[0].split("=")[1].strip())
        if npoints > 0:
            entryList = _processSectionData(sectionTuple[1])
    
    return entryList


def _processSectionData(sectionData):
    
    sectionData += "\n"
    
    startI = 0
    tupleList = []
    while True:
        try:
            startI = sectionData.index("=", startI) + 1  # Past the equal sign
        except ValueError:  # No more data
            break
        
        endI = sectionData.index("\n", startI)
        time = float(sectionData[startI:endI].strip())
        
        startI = sectionData.index("=", endI) + 1  # Just past the '=' sign
        endI = sectionData.index("\n", startI)
        value = float(sectionData[startI:endI].strip())
        
        startI = endI
        tupleList.append((time, value))
        
    return tupleList


def _cleanNumericValues(dataStr):
    dataList = dataStr.split("\n")
    newDataList = []
    for row in dataList:
        row = row.rstrip()
        try:
            head, tail = row.split("=")
            head = head.rstrip()
            tail = tail.strip()
            try:
                row = str(int(tail))
            except ValueError:
                tail = "%s" % tail
                if float(tail) == 0:
                    tail = "0"
            row = "%s = %s" % (head, tail)
        except ValueError:
            pass
        finally:
            newDataList.append(row.rstrip())
    
    outputTxt = "\n".join(newDataList)
    
    return outputTxt