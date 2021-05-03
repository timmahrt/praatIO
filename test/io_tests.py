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
import io
from os.path import join


from praatio import textgrid
from praatio.utilities import constants
from praatio.utilities import textgrid_io
from praatio.utilities import errors

from test.testing_utils import areTheSameFiles
from test.praatio_test_case import PraatioTestCase


def readFile(fn):
    with io.open(fn, "r") as fd:
        return fd.read()


def run_save(
    tg,
    minimumIntervalLength=None,
    minTimestamp=None,
    maxTimestamp=None,
    ignoreBlankSpaces=False,
):
    """
    Mock write function and return the first tier's entry list

    tg.save() mutates the textgrid's data, so the entry list
    before and after saving can be different
    """

    tgAsDict = textgrid._tgToDictionary(tg)
    textgrid_io.getTextgridAsStr(
        tgAsDict,
        minimumIntervalLength=minimumIntervalLength,
        minTimestamp=minTimestamp,
        maxTimestamp=maxTimestamp,
        ignoreBlankSpaces=ignoreBlankSpaces,
    )

    entryList = tgAsDict["tiers"][0]["entries"]
    entryList = [[start, end, label] for start, end, label in entryList]

    return entryList


class IOTests(PraatioTestCase):
    """Testing input and output"""

    def test_reading_textgrids_with_newlines_in_labels(self):
        """Tests for reading/writing textgrids with newlines"""
        fn = "bobby_words_with_newlines.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN)
        tg.save(outputFN)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_reading_long_textgrids_with_newlines_in_labels(self):
        """Tests for reading/writing textgrids with newlines"""
        fn = "bobby_words_with_newlines_longfile.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN)
        tg.save(outputFN, outputFormat=constants.TextgridFormats.LONG_TEXTGRID)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_tg_io(self):
        """Tests for reading/writing textgrid io"""
        fn = "textgrid_to_merge.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN)
        tg.save(outputFN)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_tg_io_long_vs_short(self):
        """Tests reading of long vs short textgrids"""

        shortFN = join(self.dataRoot, "textgrid_to_merge.TextGrid")
        longFN = join(self.dataRoot, "textgrid_to_merge_longfile.TextGrid")

        self.assertTrue(areTheSameFiles(shortFN, longFN, textgrid.openTextgrid))

    def test_saving_short_textgrid(self):
        """Tests that short textgrid files are saved non-destructively"""
        fn = "textgrid_to_merge.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_short_file.textgrid")

        tg = textgrid.openTextgrid(shortFN)
        tg.save(outputFN, outputFormat=constants.TextgridFormats.SHORT_TEXTGRID)

        self.assertTrue(areTheSameFiles(shortFN, outputFN, readFile))

    def test_saving_long_textgrid(self):
        """Tests that long textgrid files are saved non-destructively"""
        fn = "textgrid_to_merge_longfile.TextGrid"
        longFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_long_file.textgrid")

        tg = textgrid.openTextgrid(longFN)
        tg.save(outputFN, outputFormat=constants.TextgridFormats.LONG_TEXTGRID)

        self.assertTrue(areTheSameFiles(longFN, outputFN, readFile))

    def test_saving_and_loading_json(self):
        """Tests that json files are saved non-destructively"""
        fn = "mary.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_textgrid_as_json.json")
        outputLastFN = join(
            self.outputRoot, "saved_textgrid_as_json_then_textgrid.TextGrid"
        )

        tgFromTgFile = textgrid.openTextgrid(shortFN)
        tgFromTgFile.save(outputFN, outputFormat=constants.TextgridFormats.JSON)

        tgFromJsonFile = textgrid.openTextgrid(outputFN)
        tgFromJsonFile.save(outputLastFN)

        self.assertTrue(areTheSameFiles(shortFN, outputLastFN, readFile))

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

        tier = textgrid.IntervalTier("test", userEntryList, 0, 2.0)
        tg = textgrid.Textgrid()
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

        tier = textgrid.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = textgrid.Textgrid()
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

        tier = textgrid.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = textgrid.Textgrid()
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

        tier = textgrid.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, maxTimestamp=3.0)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_force_too_small_minimum_time(self):
        # If you choose to force save to use a minTimestamp, all
        # of your entries must be higher than that minTimestamp
        userEntryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]

        tier = textgrid.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)

        self.assertRaises(errors.ParsingError, run_save, tg, minTimestamp=1.0)

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

        tier = textgrid.IntervalTier("test", userEntryList, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, minimumIntervalLength=0.06)

        self.assertEqual(expectedEntryList, actualEntryList)

    def test_save_with_ignore_blank_sections(self):
        """
        Tests that blank sections can be ignored on saving a textgrid
        """
        entryList = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntryList = entryList  # Blank intervals should not be inserted
        tier = textgrid.IntervalTier("test", entryList)

        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntryList = run_save(tg, ignoreBlankSpaces=True)

        self.assertEqual(expectedEntryList, actualEntryList)


if __name__ == "__main__":
    unittest.main()
