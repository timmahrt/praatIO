
This guide outlines steps to upgrading between versions.

For more information about the most recent version of Praatio, please see the documentation linked in the README file.

If you are having difficulty upgrading, please don't hesistate to open an issue or contact me.

# Table of contents
1. [Version 6 to 7](#version-6-to-7-migration)
2. [Version 5 to 6](#version-5-to-6-migration)
3. [Version 4 to 5](#version-4-to-5-migration)

## Version 6 to 7 Migration

### praatio_scripts.py

splitTierEntries has a simplified signature.
"startT" and "endT" have been removed.
Please prepare your textgrid (e.g. tg.crop()) before calling splitTierEntries.

splitAudioOnTier has a slightly new signature
- the options for nameStyle have been changed to better reflect the available options
  - "append" -> "name_and_i_and_label"
  - "append_no_i" -> "name_and_label"
  - None -> "name_and_label"
- "noPartialIntervals" -> "allowPartialIntervals" to avoid a double negative

tgBoundariesToZeroCrossings was removed
- use the new TextgridTier.toZeroCrossings() method instead

alignBoundariesAcrossTiers was removed
- use the new TextgridTier.dejitter() method instead

### interval_tier.py

insertSpace raises CollisionError rather than ArgumentError when the space to insert overlaps
with an existing entry and the collisionMode is "error".

## Version 5 to 6 Migration

### JSON output files

Before there was only one JSON output schema. Now there are two.

'JSON' and 'Textgrid JSON'.
See [README.md](https://github.com/timmahrt/praatIO/blob/main/CHANGELOG.md) for more information.

`textgrid.openTextgrid()` will correctly open either JSON variant.

`textgrid.Textgrid.save()` takes an argument `format`.
If you wish to keep the same behavior as in Praatio 5.0, please specify `format=textgrid_json`.

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

### data_classes/textgrid.py

`Textgrid.tierDict` has been made protected
  - Instead of using with `Textgrid.tierDict` directly, please use `Textgrid.addTier()`, `Textgrid.getTier()`, `Textgrid.removeTier()`, and `Textgrid.renameTier()`
  - Instead of `Textgrid.tierDict.keys()` use `Textgrid.tierNames`
  - Instead of `Textgrid.tierDict.values()` use `Textgrid.tiers`

### data_classes/textgrid_tier.py

`TextgridTier.entryList` was renamed to `TextgridTier.entries` and made read only. Please use `TextgridTier.insertEntry()` and `TextgridTier.deleteEntry()` if you need to modify it.

### praatio_scripts.py

`alignBoundariesAcrossTiers` has an additional required argument, `tierName` which is the name of the reference tier used
to determine "correct" alignment.

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
  format="short_textgrid",
  includeBlankSpaces=True
)
```

Please consult the documentation to help in upgrading to version 5.
