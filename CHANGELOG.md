
# Praatio Changelog

*Praatio uses semantic versioning (Major.Minor.Patch)*

Ver 6.0 (Feb 4, 2023)
- Refactored 'audio.py' for maintainability (see [UPGRADING.md](https://github.com/timmahrt/praatIO/blob/main/UPGRADING.md) for details)
- Added unit tests for 'audio.py'
- Fixed several bugs related to audio.py
    - Fixed an issue related to finding zero crossings when a value of zero does not appear in the current sample
    - Fixed a rounding issue in several methods (`openAudioFile`, `insert`, `generateSineWave`, `generateSilence`). The rounding error would lead to minor miscalculations. But if the calculations were run many times, the errors would accumulate and become more noticable.
    - Fixed an issue with `readFramesAtTimes`. When the parameter `keepList` or `deleteList` was set, the wrong segments would be kept or deleted.
- Adjusted how Textgrids are used
    - Textgrid.tierDict has been made private
        - Instead of using with tg.tierDict directly, please use tg.addTier, tg.getTier, tg.removeTier, and tg.renameTier
        - Instead of tg.tierDict.keys() use Textgrid.tierNameList


Ver 5.1 (Dec 31, 2021)
- Fuzzy equivalence for timestamps in Intervals and Points

Ver 5.0 (Aug 8, 2021)
- Type Annotations
- Dropping support for Python < 3.7 (including 2.x)
- Change from asserts to custom exception classes
- Unit tests (WIP)
- Textgrid state validation
- Lots of bugfixes
- Option for reading textgrids that contain tiers with the same name
- Housekeeping
    - break 'tgio' into smaller files
        - all the old tgio content is still exposed in tgio (now called 'textgrid') via imports
    - rename 'tgio' -> 'textgrid'; 'kgio' -> 'klattgrid'; 'audioio' -> 'audio'; 'dataio' -> 'data_points'
    - move the changelog out of the README file
    - changed the interface of openTextgrid and tg.save() to have fewer unexpected results


Ver 4.4 (Jul 5, 2021)
- Textgrid reading now more robust (fix for files created in Elan)

Ver 4.3 (Apr 5, 2021)
- Textgrid reading/writing is now more robust (newlines and quotes are ok)
- Textgrids can now be saved without creating blank intervals
    - For backwards compatibility, by default, segments with no intervals will be given a blank entry with a label of ""

Ver 4.2 (Aug 14, 2020)
- Textgrids can now be written to/read from a json file
    - tg.save("blah.json", format=tgio.JSON)
    - tg = openTextgrid("blah.json", readAsJson=True)

Ver 4.1 (May 13, 2020)
- Textgrids can now be read "raw"
    - For backwards compatibility, by default, unlabeled points and intervals are removed when opening textgrids

Ver 4.0 (February 5, 2020)
- Removed unlicensed xsampa.py file, along with associated utility sppas_util.py (originally added in Ver 3.4)
    - If you are not directly importing either of those files, you can upgrade without changing your code

Ver 3.8 (July 24, 2019)
- Textgrids can be saved in the Textgrid long file format with .save(fn, useShortForm=False).
    - For backwards compatibility, by default, it saves in the short file format.
- Textgrid output formatting is now closer to what Praat outputs.

Ver 3.7 (March 17, 2019)
- Speaker normalization and normalization within local context added to pitch and intensity query functions
- Generated pdoc documentation added

Ver 3.6 (May 05, 2017)
- Major clean up of tgio
    - Ver 3.6 is **not** backwards compatible with previous versions of PraatIO.  Lots of changes to tgio.
- Tutorials folder added


Ver 3.5 (April 04, 2017)
- Added code for reading, writing, and manipulating audio files (praatio.audioio)
- *eraseRegion()* and *insertRegion()* added to textgrids and textgrid tiers


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
