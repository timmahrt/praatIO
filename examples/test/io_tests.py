"""
Created on Jan 27, 2016

@author: tmahrt

Tests that praat files can be read in and then written out, and that the two
resulting files are the same.

This does not test that the file reader is correct.  If the file
reader is bad (e.g. truncates floating points to 1 decimal place), the
resulting data structures will look the same for both the source and
generated files.
"""

import unittest
import os
import io
from os.path import join

from praatio import tgio
from praatio import dataio
from praatio import kgio
from praatio import audioio


def areTheSame(fn1, fn2, fileHandler=None):
    """
    Tests that files contain the same data

    Usually we don't want to compare the raw text files.  There are minute
    differences in the way floating points values are.

    Also allows us to compare short and long-form textgrids
    """
    if fileHandler is None:
        fileHandler = lambda fn: open(fn, "r").read()

    data1 = fileHandler(fn1)
    data2 = fileHandler(fn2)

    return data1 == data2


def readFile(fn):
    data = ""
    with io.open(fn, "r") as fd:
        data = fd.read()
    return data


def run_save(tg, minimumIntervalLength=None, minTimestamp=None, maxTimestamp=None):
    """
    Mock write function and return the first tier's entry list

    tg.save() mutates the textgrid's data, so the entry list
    before and after saving can be different
    """

    tg.save(
        "garbage.Textgrid",
        minimumIntervalLength=minimumIntervalLength,
        minTimestamp=minTimestamp,
        maxTimestamp=maxTimestamp,
    )

    entryList = tg.tierDict[tg.tierNameList[0]].entryList
    entryList = [[start, end, label] for start, end, label in entryList]

    return entryList


class IOTests(unittest.TestCase):
    """Testing input and output"""

    def __init__(self, *args, **kargs):
        super(IOTests, self).__init__(*args, **kargs)

        cwd = os.path.dirname(os.path.realpath(__file__))
        root = os.path.split(cwd)[0]
        self.dataRoot = join(root, "files")
        self.outputRoot = join(self.dataRoot, "io_test_output")

    def setUp(self):
        if not os.path.exists(self.outputRoot):
            os.mkdir(self.outputRoot)

    def test_tg_io(self):
        """Tests for reading/writing textgrid io"""
        fn = "textgrid_to_merge.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = tgio.openTextgrid(inputFN)
        tg.save(outputFN)

        self.assertTrue(areTheSame(inputFN, outputFN, tgio.openTextgrid))

    def test_tg_io_long_vs_short(self):
        """Tests reading of long vs short textgrids"""

        shortFN = join(self.dataRoot, "textgrid_to_merge.TextGrid")
        longFN = join(self.dataRoot, "textgrid_to_merge_longfile.TextGrid")

        self.assertTrue(areTheSame(shortFN, longFN, tgio.openTextgrid))

    def test_saving_short_textgrid(self):
        """Tests that short textgrid files are saved non-destructively"""
        fn = "textgrid_to_merge.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_short_file.textgrid")

        tg = tgio.openTextgrid(shortFN)
        tg.save(outputFN)

        self.assertTrue(areTheSame(shortFN, outputFN, readFile))

    def test_saving_long_textgrid(self):
        """Tests that long textgrid files are saved non-destructively"""
        fn = "textgrid_to_merge_longfile.TextGrid"
        longFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_long_file.textgrid")

        tg = tgio.openTextgrid(longFN)
        tg.save(outputFN, useShortForm=False)

        self.assertTrue(areTheSame(longFN, outputFN, readFile))

    def test_saving_and_loading_json(self):
        """Tests that json files are saved non-destructively"""
        fn = "mary.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_textgrid_as_json.json")
        outputLastFN = join(
            self.outputRoot, "saved_textgrid_as_json_then_textgrid.TextGrid"
        )

        tgFromTgFile = tgio.openTextgrid(shortFN)
        tgFromTgFile.save(outputFN, outputFormat=tgio.JSON)

        tgFromJsonFile = tgio.openTextgrid(outputFN, readAsJson=True)
        tgFromJsonFile.save(outputLastFN)

        self.assertTrue(areTheSame(shortFN, outputLastFN, readFile))

    def test_get_audio_duration(self):
        """Tests that the two audio duration methods output the same value."""
        wavFN = join(self.dataRoot, "bobby.wav")

        durationA = tgio._getWavDuration(wavFN)
        durationB = audioio.getDuration(wavFN)
        self.assertTrue(durationA == durationB)

    def test_duration_tier_io(self):
        """Tests for reading/writing duration tiers"""
        fn = "mary.DurationTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        dt = dataio.open2DPointObject(inputFN)
        dt.save(outputFN)

        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open2DPointObject))

    def test_pitch_io(self):
        """Tests for reading/writing pitch tiers"""
        fn = "mary.PitchTier"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        pp = dataio.open2DPointObject(inputFN)
        pp.save(outputFN)

        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open2DPointObject))

    def test_pitch_io_long_vs_short(self):
        """Tests reading of long vs short 2d point objects"""

        shortFN = join(self.dataRoot, "mary.PitchTier")
        longFN = join(self.dataRoot, "mary_longfile.PitchTier")

        self.assertTrue(areTheSame(shortFN, longFN, dataio.open2DPointObject))

    def test_point_process_io(self):
        """Tests for reading/writing point processes"""
        fn = "bobby.PointProcess"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        pp = dataio.open1DPointObject(inputFN)
        pp.save(outputFN)

        self.assertTrue(areTheSame(inputFN, outputFN, dataio.open1DPointObject))

    def test_point_process_io_long_vs_short(self):

        shortFN = join(self.dataRoot, "bobby.PointProcess")
        longFN = join(self.dataRoot, "bobby_longfile.PointProcess")

        self.assertTrue(areTheSame(shortFN, longFN, dataio.open1DPointObject))

    def test_kg_io(self):
        """Tests for reading/writing klattgrids"""
        fn = "bobby.KlattGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        kg = kgio.openKlattgrid(inputFN)
        kg.save(outputFN)

        self.assertTrue(areTheSame(inputFN, outputFN, kgio.openKlattgrid))

    def test_save(self):
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0.0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_minimum_time_stamp(self):
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0.3, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_force_zero_as_minimum_time(self):
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, minTimestamp=0)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_force_larger_value_as_maximum_time(self):
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0.3, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 3.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, maxTimestamp=3.0)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_force_too_large_minimum_time(self):
        # If you choose to force save to use a minTimestamp, all
        # of your entries must be higher than that minTimestamp
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)

        self.assertRaises(AssertionError, run_save, tg, minTimestamp=1.0)

    def test_save_with_force_too_large_minimum_time(self):
        # If you choose to force save to use a minTimestamp, all
        # of your entries must be higher than that minTimestamp
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)

        self.assertRaises(AssertionError, run_save, tg, maxTimestamp=1.0)

    def test_save_with_minimum_interval_length(self):
        # The first entry will be stretched to fill the unlabeled region in
        # front of it: [0.30, 0.35, ''] (The unlabeled region starts at 0.3
        # instead of 0 because the minTimestamp for this tg is 0.3)
        userEntryList = [[0.35, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = [
            [0.3, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = tgio.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = tgio.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, minimumIntervalLength=0.06)

        self.assertEqual(expectedEntryList, actualEntryList)


if __name__ == "__main__":
    unittest.main()
