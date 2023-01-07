
# praatIO

[![](https://app.travis-ci.com/timmahrt/praatIO.svg?branch=main)](https://app.travis-ci.com/github/timmahrt/praatIO) [![](https://coveralls.io/repos/github/timmahrt/praatIO/badge.svg?)](https://coveralls.io/github/timmahrt/praatIO?branch=main) [![](https://img.shields.io/badge/license-MIT-blue.svg?)](http://opensource.org/licenses/MIT) [![](https://img.shields.io/pypi/v/praatio.svg)](https://pypi.org/project/praatio/)

*Questions?  Comments?  Feedback? [![](https://badges.gitter.im/praatio/Lobby.svg)](https://gitter.im/praatio/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)*

-----

A library for working with praat, time aligned audio transcripts, and audio files *that comes with batteries included*.

Praat uses a file format called textgrids, which are time aligned speech transcripts.
This library isn't just a data struct for reading and writing textgrids--many utilities are
provided to make it easy to work with with transcripts and associated audio files.
This library also provides some other tools for use with praat.

Praat is an open source software program for doing phonetic analysis and annotation 
of speech.  [Praat can be downloaded here](<http://www.fon.hum.uva.nl/praat/>)

# Table of contents
1. [Documentation](#documentation)
2. [Tutorials](#tutorials)
3. [Version History](#version-history)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Upgrading major versions](#upgrading)
7. [Usage](#usage)
8. [Common Use Cases](#common-use-cases)
9. [Tests](#tests)
10. [Citing praatIO](#citing-praatio)
11. [Acknowledgements](#acknowledgements)

## Documentation

Automatically generated pdocs can be found here:

http://timmahrt.github.io/praatIO/


## Tutorials

There are tutorials available for learning how to use PraatIO.  These
are in the form of IPython Notebooks which can be found in the /tutorials/
folder distributed with PraatIO.

You can view them online using the external website Jupyter:

[Tutorial 1: An introduction and tutorial](<https://nbviewer.jupyter.org/github/timmahrt/praatIO/blob/main/tutorials/tutorial1_intro_to_praatio.ipynb>)
    
    
## Version History

*Praatio uses semantic versioning (Major.Minor.Patch)*

Please view [CHANGELOG.md](https://github.com/timmahrt/praatIO/blob/main/CHANGELOG.md) for version history.


## Requirements

Python module `https://pypi.org/project/typing-extensions/`.  It should be installed automatically with praatio but you can install it manually if you have any problems.

``Python 3.7.*`` or above

[Click here to visit travis-ci and see the specific versions of python that praatIO is currently tested under](<https://travis-ci.org/timmahrt/praatIO>)

If you are using ``Python 2.x`` or ``Python < 3.7``, you can use `PraatIO 4.x`.

## Installation

PraatIO is on pypi and can be installed or upgraded from the command-line shell with pip like so

    python -m pip install praatio --upgrade

Otherwise, to manually install, after downloading the source from github, from a command-line shell, navigate to the directory containing setup.py and type

    python setup.py install

If python is not in your path, you'll need to enter the full path e.g.

    C:\Python37\python.exe setup.py install

## Upgrading

Please view [UPGRADING.md](https://github.com/timmahrt/praatIO/blob/main/UPGRADING.md) for detailed information about how to upgrade from earlier versions.

## Usage

99% of the time you're going to want to run

```python
from praatio import textgrid
tg = textgrid.openTextgrid(r"C:\Users\tim\Documents\transcript.TextGrid", False)
```

Or if you want to work with KlattGrid files

```python
from praatio import klattgrid
kg = klattgrid.openKlattGrid(r"C:\Users\tim\Documents\transcript.KlattGrid")
```

See /test for example usages


## Common Use Cases

What can you do with this library?

- query a textgrid to get information about the tiers or intervals contained within
    ```python
    tg = textgrid.openTextgrid("path_to_textgrid", False)
    entryList = tg.tierDict["speaker_1_tier"].entryList # Get all intervals
    entryList = tg.tierDict["phone_tier"].find("a") # Get the indicies of all occurrences of 'a'
    ```

- create or augment textgrids using data from other sources

- found that you clipped your audio file five seconds early and have added it back to your wavefile but now your textgrid is misaligned?  Add five seconds to every interval in the textgrid
    ```python
    tg = textgrid.openTextgrid("path_to_textgrid", False)
    moddedTG = tg.editTimestamps(5)
    moddedTG.save('output_path_to_textgrid', 'long_textgrid', True)
    ```

- utilize the klattgrid interface to raise all speech formants by 20%
    ```python
    kg = klattgrid.openKlattGrid("path_to_klattgrid")
    incrTwenty = lambda x: x * 1.2
    kg.tierDict["oral_formants"].modifySubtiers("formants",incrTwenty)
    kg.save(join(outputPath, "bobby_twenty_percent_less.KlattGrid"))
    ```

- replace labeled segments in a recording with silence or delete them
    - see /examples/deleteVowels.py

- use set operations (union, intersection, difference) on textgrid tiers
    - see /examples/textgrid_set_operations.py

- see /praatio/praatio_scripts.py for various ready-to-use functions such as
    - `splitAudioOnTier()`: split an audio file into chunks specified by intervals in one tier
    - `spellCheckEntries()`: spellcheck a textgrid tier
    - `tgBoundariesToZeroCrossings()`: adjust all boundaries and points to fall at the nearest zero crossing in the corresponding audio file
    - `alignBoundariesAcrossTiers()`: for handmade textgrids, sometimes entries may look as if they are aligned at the same time but actually are off by a small amount, this will correct them


## Tests

I run tests with the following command (this requires pytest and pytest-cov to be installed):

`pytest --cov=praatio tests/`

## Citing praatIO

PraatIO is general purpose coding and doesn't need to be cited
but if you would like to, it can be cited like so:

Tim Mahrt. PraatIO. https://github.com/timmahrt/praatIO, 2016.


## Acknowledgements

Development of PraatIO was possible thanks to NSF grant **BCS 12-51343** to
Jennifer Cole, José I. Hualde, and Caroline Smith and to the A\*MIDEX project
(n° **ANR-11-IDEX-0001-02**) to James Sneed German funded by the
Investissements d'Avenir French Government program,
managed by the French National Research Agency (ANR).
