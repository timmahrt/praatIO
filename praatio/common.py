'''
Created on Oct 30, 2015

@author: tmahrt
'''

import os
from os.path import join
import subprocess

import inspect

# Get the folder one level above the current folder
praatioPath = os.path.split(inspect.getfile(inspect.currentframe()))[0]
scriptsPath = join(praatioPath, "praatScripts")
def findAll(txt, subStr):
    
    indexList = []
    index = 0
    while True:
        try:
            index = txt.index(subStr, index)
        except ValueError:
            break
        indexList.append(int(index))
        index += 1
    
    return indexList


def runPraatScript(praatEXE, scriptFN, argList, exitOnError=True):
    
    argList = ["%s" % arg for arg in argList]
    cmdList = [praatEXE, '--run', scriptFN] + argList
    myProcess = subprocess.Popen(cmdList)
 
    if myProcess.wait() and exitOnError:
        exit()
