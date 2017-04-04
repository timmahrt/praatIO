
---------
praatIO
---------

.. image:: https://travis-ci.org/timmahrt/praatIO.svg?branch=master
    :target: https://travis-ci.org/timmahrt/praatIO

.. image:: https://coveralls.io/repos/github/timmahrt/praatIO/badge.svg?branch=master
    :target: https://coveralls.io/github/timmahrt/praatIO?branch=master

.. image:: https://img.shields.io/badge/license-MIT-blue.svg?
    :target: http://opensource.org/licenses/MIT

A library for working with praat, time aligned audio transcripts, and audio files *that comes with batteries included*.
Praat uses a file format called textgrids, which are time aligned speech transcripts.
This library isn't just a data struct for reading and writing textgrids--many utilities are
provided to make it easy to work with with transcripts and associated audio files.
This library also provides some other tools for use with praat.

Praat is an open source software program for doing phonetic analysis and annotation 
of speech.  `Praat can be downloaded here <http://www.fon.hum.uva.nl/praat/>`_

.. sectnum::
.. contents::

Common Use Cases
================

What can you do with this library?

- query a textgrid to get information about the tiers or intervals contained within::

    tg = tgio.openTextGrid("path_to_textgrid")

    entryList = tg.tierDict["speaker_1_tier"].getEntries() # Get all intervals

    entryList = tg.tierDict["phone_tier"].find("a") # Get all instances of 'a'

- create or augment textgrids using data from other sources

- found that you clipped your audio file five seconds early and have added it back to your wavefile but now your textgrid is misaligned?  Add five seconds to every interval in the textgrid::

    tg = tgio.openTextGrid("path_to_textgrid")

    moddedTG = tg.editTimestamps(5, 5, 5)

    moddedTG.save('output_path_to_textgrid')
    
- manipulate an audio file based on information in a textgrid::

    see splitAudioOnTier() in /praatio/praatio_scripts.py
    
- remove all intervals (and associated intervals in other tiers) that don't match a query.::

    # This would remove all words that are not content words from the word_tier 

    # and also remove their associated phone listings in the phone_tier

    tg = tgio.openTextGrid("path_to_textgrid")

    print(tg.tierNameList)

    >> ["word_tier", "phone_tier"]

    subTG = tg.getSubtextgrid("word_tier", isContentWord, True)

    subTG.save('output_path_to_textgrid')
    
- utilize the klattgrid interface to raise all speech formants by 20% (among other possible manipulations)::

    tg = tgio.openTextGrid("path_to_textgrid")
    
    incrTwenty = lambda x: x * 1.2
    
    kg.tierDict["oral_formants"].modifySubtiers("formants",incrTwenty)

    kg.save(join(outputPath, "bobby_twenty_percent_less.KlattGrid"))
    
- replace labeled segments in a recording with silence or delete them

    see /examples/deleteVowels.py
    
- use set operations (union, intersection, difference) on textgrid tiers

    see /examples/textgrid_set_operations.py


Major revisions
================

Ver 3.5 (April 04, 2017)

- Added code for reading, writing, and manipulating audio files (praatio.audioio)

- eraseRegion() and insertRegion() added to textgrids and textgrid tiers


Ver 3.4 (February 04, 2017)

- Added place for very specific scripts (praatio.applied_scripts)

    - added code for using with input and output textgrids to SPPAS, a forced aligner

- Lots of minor features and bugfixes


Ver 3.3 (June 27, 2016)

- Find zero-crossings in a wave file

   - for shifting all boundaries in a textgrid see *praatio_scripts.tgBoundariesToZeroCrossings()*
   
   - for finding individual zero crossings, see *praatio_scripts.findNearestZeroCrossing()*

- Pitch features

   - pitch extraction is now ten times faster
   
   - automatic pitch halving/doubling detection
   
   - median filtering

- Textgrid features

   - set operations over two tiers (union, difference, or intersection)
   
   - erase a section of a textgrid (and a section of the corresponding wave file)

- Extraction of pitch formants using praat

- Lots of small bugfixes


Ver 3.2 (January 29, 2016)

- Float precision is now preserved in file I/O

- Integration tests added; using Travis CI and Coveralls for build automation.

- Lots of small bugfixes

- Moved point processes into 1D and 2D point objects


Ver 3.1 (December 16, 2015)

- Support for reading/writing point processes


Ver 3.0 (November 10, 2015)

- Support for reading and writing klattgrids


Ver 2.1 (July 27, 2015)

- Addition of praatio_scripts.py where commonly used scripts will be placed

- Import clash led to praatio.py being renamed to tgio.py


Ver 2.0 (February 5, 2015)

- Support for reading, writing, and manipulating **point** tiers

- Ported to python 3

- Major cleanup/reorganizing of code


Ver 1.0 (August 31, 2014)

- Reading and writing of textgrids

- Support for reading, writing, and manipulating **interval** tiers


Requirements
==============

``Python 2.6.*`` or above

``Python 3.3.*`` or above

`Click here to see the specific versions of python that praatIO is tested under <https://travis-ci.org/timmahrt/praatIO>`_


Usage
=========

99% of the time you're going to want to run::

    from praatio import tgio
    tg = tgio.openTextGrid(r"C:\Users\tim\Documents\transcript.TextGrid")

Or if you want to work with KlaatGrid files::

    from praatio import kgio
    kg = kgio.openKlattGrid(r"C:\Users\tim\Documents\transcript.KlattGrid")

See /test for example usages


Installation
================

If you on Windows, you can use the installer found here (check that it is up to date though)
`Windows installer <http://www.timmahrt.com/python_installers>`_

Otherwise, to manually install, after downloading the source from github, from a command-line shell, navigate to the directory containing setup.py and type::

    python setup.py install

If python is not in your path, you'll need to enter the full path e.g.::

	C:\Python27\python.exe setup.py install


Citing praatIO
===============

PraatIO is general purpose coding and doesn't need to be cited
but if you would like to, it can be cited like so:

Tim Mahrt. PraatIO. https://github.com/timmahrt/praatIO, 2016.


Acknowledgements
================

Development of PraatIO was possible thanks to NSF grant **BCS 12-51343** to
Jennifer Cole, José I. Hualde, and Caroline Smith and to the A*MIDEX project
(n° **ANR-11-IDEX-0001-02**) to James Sneed German funded by the
Investissements d'Avenir French Government program,
managed by the French National Research Agency (ANR).
