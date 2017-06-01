'''
Created on Feb 04, 2017

Demonstrates the code that preps and cleans up the input and output of sppas

@author: tmahrt
'''

from os.path import join
import shutil

from praatio.applied_scripts import sppas_util

rootPath = r".\files\sppas_output"
outputPath = join(rootPath, "cleaned")
shutil.copy(join(".", "files", "bobby.wav"), join(rootPath, "bobby.wav"))
shutil.copy(join(".", "files", "bobby.txt"), join(rootPath, "bobby.txt"))

# 1st, run this.  2nd run SPPAS, which generates bobby.TextGrid
# sppas_util.generateSingleIPUTextgrids(rootPath, rootPath, rootPath)

# 3rd, run this to clean up the results of SPPAS
sppas_util.sppasPostProcess(rootPath,
                            outputPath,
                            deleteIntermediateFiles=False)
