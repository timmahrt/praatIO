
---------
praatIO
---------

A library that facilitates working with praat and praat files.

Praat is a software program for doing phonetic analysis and annotation 
of speech.  `Praat can be downloaded here <http://www.fon.hum.uva.nl/praat/>`_

Very much a work in progress.  This will house various resources that I 
use in working with praat.


Requirements
==============

``Python 2.7.*`` or above

``Python 3.3.*`` or above


Usage
=========

99% of the time you're going to want to run::

    import praatio
    tg = praatio.openTextGrid(r"C:\Users\tim\Documents\transcript.TextGrid")

See /test for example usages


Installation
================

Navigate to the directory this is located in and type::

	python setup.py install

If python is not in your path, you'll need to enter the full path e.g.::

	C:\Python27\python.exe setup.py install

