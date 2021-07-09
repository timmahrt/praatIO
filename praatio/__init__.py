"""
Praatio is a library for working praat files and audio data.

Praat is a popular tool for working with transcribed speech data.
It has tools for annotating speech, manipulating speech, and extracting
information from speech.
Praat's homepage: [http://www.fon.hum.uva.nl/praat/](http://www.fon.hum.uva.nl/praat/)

praatio's utility comes from the classes Textgrid, IntervalTier,
and PointTier in **textgrid.py** These classes represent the speech transcript
data stored inside of .TextGrid files.  textgrid.py contains functions for
reading/writing these objects from/to files. **data_points.py** and **klattgrid.py**
contain similar code for other data files that praat works with.

**pitch_and_intensity.py** uses praat to extract pitch and intensity values
from audio using praat.

**praat_scripts.py** enables one to run various praat scripts from within python.
If preferred, one can access the **praatScripts/** directory to view and edit the
praat scripts or open them directly in praat. They can all be run independentlyof python.

**audio.py** is for reading, reading, and performing simple manipulations to wave files.

**praatio_scripts.py** contains code that combines various code in praatio--mostly
high-level functions for working with textgrids, sometimes in conjuction with audio files.

For example scripts that use various parts of the praatio library, please see 'examples/'
in the root directory. If you downloaded praatio from pip, you can get the example files
on the praatio github page:
[https://github.com/timmahrt/praatIO](https://github.com/timmahrt/praatIO)

There is also a tutorial for working with praatio on the github page.
"""
