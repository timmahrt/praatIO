
This guide outlines steps to upgrading between versions.

For more information about the most recent version of Praatio, please see the documentation linked in the README file.

If you are having difficulty upgrading, please don't hesistate to open an issue or contact me.

# Table of contents
1. [Version 5 to 6](#version-5-to-6-migration)
2. [Version 4 to 5](#version-4-to-5-migration)

## Version 5 to 6 Migration

### audio.py

audio.py has been refreshed in version 6 with numerous bugfixes and
api changes.

Renamed methods and classes

- audio.WavQueryObj -> audio.QueryWav
- audio.WavObj -> audio.Wav
(the new names of these classes are used below)

- audio.samplesAsNums -> audio.convertFromBytes
- audio.numsAsSamples -> audio.convertToBytes
- audio.getMaxAmplitude -> audio.calculateMaxAmplitude
- audio.AbstractWav.getDuration -> audio.AbstractWav.duration
- audio.Wav.getSubsegment -> audio.Wav.getSubwav

Moved methods
- audio.generateSineWave -> audio.AudioGenerator.generateSineWave
- audio.generateSilence -> audio.AudioGenerator.generateSilence
- audio.openAudioFile -> audio.readFramesAtTimes
- audio.WavQuery.concatenate -> audio.Wav.concatenate

Removed methods
- audio.WavQuery.deleteWavSections
- audio.WavQuery.outputModifiedWav
- audio.Wav.getIndexAtTime (made private)
- audio.Wav.insertSilence (use audio.Wav.insert and audio.AudioGenerator.generateSilence instead)

Added methods
- audio.Wav.replaceSegment
- audio.Wav.open

## Version 4 to 5 Migration

Many things changed between versions 4 and 5.  If you see an error like
`WARNING: You've tried to import 'tgio' which was renamed 'textgrid' in praatio 5.x.`
it means that you have installed version 5 but your code was written for praatio 4.x or earlier.

The immediate solution is to uninstall praatio 5 and install praatio 4. From the command line:
```
pip uninstall praatio
pip install "praatio<5"
```

If praatio is being installed as a project dependency--ie it is set as a dependency in setup.py like
```
    install_requires=["praatio"],
```
then changing it to the following should fix the problem
```
    install_requires=["praatio ~= 4.1"],
```

Many files, classes, and functions were renamed in praatio 5 to hopefully be clearer.  There
were too many changes to list here but the `tgio` module was renamed `textgrid`.

Also, the interface for `openTextgrid()` and `tg.save()` has changed. Here are examples of the required arguments in the new interface
```
textgrid.openTextgrid(
  fn=name,
  includeEmptyIntervals=False
)
```
```
tg.save(
  fn=name,
  format= "short_textgrid",
  includeBlankSpaces= False
)
```

Please consult the documentation to help in upgrading to version 5.
