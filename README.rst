
---------
praatIO
---------

.. image:: https://travis-ci.org/timmahrt/praatIO.svg?branch=master
    :target: https://travis-ci.org/timmahrt/praatIO

.. image:: https://coveralls.io/repos/github/timmahrt/praatIO/badge.svg?branch=master
    :target: https://coveralls.io/github/timmahrt/praatIO?branch=master

A library for working with praat and praat files *that comes with batteries included*.
This isn't just a data struct for reading and writing textgrids--many utilities are
provided to make it easy to work with textgrid data.

Praat is a software program for doing phonetic analysis and annotation 
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


Major revisions
================

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

``Python 2.7.*`` or above

``Python 3.3.*`` or above


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

Navigate to the directory this is located in and type::

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

Development of PraatIO was possible thanks to NSF grant **BCS 12-51343**
to Jennifer Cole, José Hualde, and Caroline Smith.
