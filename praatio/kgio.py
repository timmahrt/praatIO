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

import io
from os.path import join

from praatio.utilities import utils
from praatio import tgio


class _KlattBaseTier(object):

    def __init__(self, name):
        self.tierNameList = []  # Preserves the order of the tiers
        self.tierDict = {}
        self.name = name
        self.minTimestamp = None
        self.maxTimestamp = None
    
    def __eq__(self, other):
        isEqual = True
        isEqual &= self.name == other.name
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
        if self.minTimestamp is None or (minV is not None and
                                         minV < self.minTimestamp):
            self.minTimestamp = minV
        
        maxV = tier.maxTimestamp
        if self.maxTimestamp is None or (maxV is not None and
                                         maxV > self.maxTimestamp):
            self.maxTimestamp = maxV


class KlattContainerTier(_KlattBaseTier):
    '''
    Contains a set of intermediate tiers
    '''
    def getAsText(self):
        outputTxt = ""
        outputTxt += "%s? <exists>\n" % self.name
        
        try:
            self.minTimestamp = toIntOrFloat(self.minTimestamp)
            outputTxt += "xmin = %s\nxmax = %s\n" % (repr(self.minTimestamp),
                                                     repr(self.maxTimestamp))
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
    
    
class KlattIntermediateTier(_KlattBaseTier):
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
    

class KlattPointTier(tgio.TextgridTier):
    '''
    A Klatt tier not contained within another tier
    '''
    
    def __init__(self, name, entryList, minT=None, maxT=None):
        
        entryList = [(float(time), label) for time, label in entryList]
        
        # Determine the min and max timestamps
        timeList = [time for time, label in entryList]
        if minT is not None:
            timeList.append(float(minT))
        if maxT is not None:
            timeList.append(float(maxT))
        
        try:
            minT = min(timeList)
            maxT = max(timeList)
        except ValueError:
            raise tgio.TimelessTextgridTierException()

        super(KlattPointTier, self).__init__(name, entryList, minT, maxT)
    
    def modifyValues(self, modFunc):
        newEntryList = [(timestamp, modFunc(float(value)))
                        for timestamp, value in self.entryList]
        
        self.entryList = newEntryList
        
    def getAsText(self):
        outputList = []
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("%s? <exists> " % self.name)
        outputList.append("xmin = %s" % repr(self.minTimestamp))
        outputList.append("xmax = %s" % repr(self.maxTimestamp))
        
        if self.name not in ["phonation", "vocalTract", "coupling",
                             "frication"]:
            outputList.append("points: size= %d" % len(self.entryList))
        
        for i, entry in enumerate(self.entryList):
            outputList.append("points [%d]:" % (i + 1))
            outputList.append("    number = %s" % repr(entry[0]))
            outputList.append("    value = %s" % repr(entry[1]))
    
        return "\n".join(outputList) + "\n"


class KlattSubPointTier(KlattPointTier):
    '''
    Tiers contained in a KlattIntermediateTier
    '''
        
    def getAsText(self):
        outputList = []
        outputList.append("%s:" % self.name)
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputList.append("    xmin = %s" % repr(self.minTimestamp))
        outputList.append("    xmax = %s" % repr(self.maxTimestamp))
        outputList.append("    points: size = %d" % len(self.entryList))
        
        for i, entry in enumerate(self.entryList):
            outputList.append("    points [%d]:" % (i + 1))
            outputList.append("        number = %s" % repr(entry[0]))
            outputList.append("        value = %s" % repr(entry[1]))
    
        return "\n".join(outputList) + '\n'
    
    
class Klattgrid(tgio.Textgrid):
    
    def save(self, fn):
        
        # Header
        outputTxt = ""
        outputTxt += 'File type = "ooTextFile"\n'
        outputTxt += 'Object class = "KlattGrid"\n\n'
        self.minTimestamp = toIntOrFloat(self.minTimestamp)
        outputTxt += "xmin = %s\nxmax = %s\n" % (repr(self.minTimestamp),
                                                 repr(self.maxTimestamp))
        
        for tierName in self.tierNameList:
            outputTxt += self.tierDict[tierName].getAsText()
        
        outputTxt = _cleanNumericValues(outputTxt)
        
        with io.open(fn, "w", encoding="utf-8") as fd:
            fd.write(outputTxt)
    

def openKlattGrid(fnFullPath):

    try:
        with io.open(fnFullPath, "r", encoding="utf-16") as fd:
            data = fd.read()
    except UnicodeError:
        with io.open(fnFullPath, "r", encoding="utf-8") as fd:
            data = fd.read()
    data = data.replace("\r\n", "\n")

    # Right now, can only open normal klatt grid and not short ones
    kg = _openNormalKlattGrid(data)

    return kg


def wavToKlattGrid(praatEXE, inputFullPath, outputFullPath, timeStep=0.005,
                   numFormants=5, maxFormantFreq=5500.0, windowLength=0.025,
                   preEmphasis=50.0, pitchFloor=60.0, pitchCeiling=600.0,
                   minPitch=50.0, subtractMean=True,
                   scriptFN=None):
    '''
    Extracts the klattgrid from a wav file
    
    The default values are the same as the ones used in praat
    '''
    
    if subtractMean is True:
        subtractMean = "yes"
    else:
        subtractMean = "no"
    
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath, "sound_to_klattgrid.praat")
    
    utils.runPraatScript(praatEXE, scriptFN,
                         [inputFullPath, outputFullPath, timeStep,
                          numFormants, maxFormantFreq, windowLength,
                          preEmphasis, pitchFloor, pitchCeiling,
                          minPitch, subtractMean])


def resynthesize(praatEXE, wavFN, klattFN, outputWavFN, doCascade=True,
                 scriptFN=None):
    
    if doCascade:
        method = "Cascade"
    else:
        method = "Parallel"
    
    if scriptFN is None:
        scriptFN = join(utils.scriptsPath,
                        "resynthesize_from_klattgrid.praat")
    
    #  Praat crashes on exit after resynthesis with a klaatgrid
    utils.runPraatScript(praatEXE, scriptFN,
                         [wavFN, klattFN, outputWavFN, method])


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
    
    for i in range(len(sectionIndexList) - 1):
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
        for j in range(len(indexList) - 1):
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
    indexList = utils.findAll(data, keyword)
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
            assert("min" not in row and "max" not in row)
            
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
        except (ValueError, AssertionError):
            pass
        finally:
            newDataList.append(row.rstrip())
    
    outputTxt = "\n".join(newDataList)
    
    return outputTxt


def toIntOrFloat(val):
    if float(val) - float(int(val)) == 0.0:
        val = int(val)
    else:
        val = float(val)
    return val
