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
from praatio.data_classes import textgrid as tg_data_class
from praatio.utilities import constants
from praatio.utilities import textgrid_io
from praatio.utilities import errors

from tests.testing_utils import areTheSameFiles
from tests.praatio_test_case import PraatioTestCase


def readFile(fn):
    with io.open(fn, "r") as fd:
        return fd.read()


def run_save(
    tg,
    includeBlankSpaces=True,
    minTimestamp=None,
    maxTimestamp=None,
    minimumIntervalLength=None,
):
    """
    Mock write function and return the first tier's entry list.

    tg.save() mutates the textgrid's data, so the entry list
    before and after saving can be different.
    """

    tgAsDict = tg_data_class._tgToDictionary(tg)
    textgrid_io.getTextgridAsStr(
        tgAsDict,
        format=constants.TextgridFormats.SHORT_TEXTGRID,
        includeBlankSpaces=includeBlankSpaces,
        minTimestamp=minTimestamp,
        maxTimestamp=maxTimestamp,
        minimumIntervalLength=minimumIntervalLength,
    )

    entries = tgAsDict["tiers"][0]["entries"]
    entries = [[start, end, label] for start, end, label in entries]

    return entries


class TestIo(PraatioTestCase):
    """Test input and output."""

    def test_reading_textgrids_with_newlines_in_labels(self):
        """Tests for reading/writing textgrids with newlines."""
        fn = "bobby_words_with_newlines.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN, False)
        tg.save(outputFN, constants.TextgridFormats.SHORT_TEXTGRID, True)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_reading_long_textgrids_with_newlines_in_labels(self):
        """Tests for reading/writing textgrids with newlines."""
        fn = "bobby_words_with_newlines_longfile.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN, False)
        tg.save(outputFN, constants.TextgridFormats.LONG_TEXTGRID, True)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_reading_short_textgrids_with_start_times_of_negative_zero(self):
        """Tests for reading/writing textgrids with negative zero."""
        fn = "mary.TextGrid"
        inputFN = join(self.dataRoot, fn)
        baselineTg = textgrid.openTextgrid(inputFN, False)

        fn = "mary_with_negative_zero.TextGrid"
        negativeZeroTgFn = join(self.dataRoot, fn)
        sut = textgrid.openTextgrid(negativeZeroTgFn, False)

        self.assertEqual(baselineTg, sut)

    def test_reading_long_textgrids_with_start_times_of_negative_zero(self):
        """Tests for reading/writing textgrids with negative zero."""
        fn = "mary_longfile.TextGrid"
        inputFN = join(self.dataRoot, fn)
        baselineTg = textgrid.openTextgrid(inputFN, False)

        fn = "mary_longfile_with_negative_zero.TextGrid"
        negativeZeroTgFn = join(self.dataRoot, fn)
        sut = textgrid.openTextgrid(negativeZeroTgFn, False)

        self.assertEqual(baselineTg, sut)

    def test_tg_io(self):
        """Tests for reading/writing textgrid io."""
        fn = "textgrid_to_merge.TextGrid"
        inputFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, fn)

        tg = textgrid.openTextgrid(inputFN, False)
        tg.save(outputFN, constants.TextgridFormats.SHORT_TEXTGRID, True)

        self.assertTrue(areTheSameFiles(inputFN, outputFN, readFile))

    def test_open_textgrid_raises_error_if_mode_invalid(self):
        fn = "all_tiers_have_the_same_name.TextGrid"
        inputFN = join(self.dataRoot, fn)

        with self.assertRaises(errors.WrongOption) as cm:
            textgrid.openTextgrid(inputFN, False, duplicateNamesMode="cats")

        self.assertEqual(
            (
                "For argument 'duplicateNamesMode' was given the value 'cats'. "
                "However, expected one of [error, rename]"
            ),
            str(cm.exception),
        )

    def test_openTextgrid_throws_error_when_textgrid_has_duplicate_tier_names(self):
        fn = "all_tiers_have_the_same_name.TextGrid"
        inputFN = join(self.dataRoot, fn)

        with self.assertRaises(errors.DuplicateTierName) as cm:
            textgrid.openTextgrid(
                inputFN,
                False,
                duplicateNamesMode=constants.DuplicateNames.ERROR,
            )

        self.assertEqual(
            (
                "Your textgrid contains tiers with the same name 'Mary'. "
                "This is not allowed. It is recommended that you rename them. "
                "If you set openTextgrid(..., duplicateNamesMode='rename'), praatio "
                "will automatically append numbers to the end of tiers to ensure they "
                "are unique."
            ),
            str(cm.exception),
        )

    def test_openTextgrid_can_rename_tiers_when_textgrid_has_duplicate_tier_names(self):
        fn = "all_tiers_have_the_same_name.TextGrid"
        inputFN = join(self.dataRoot, fn)

        sut = textgrid.openTextgrid(
            inputFN, False, duplicateNamesMode=constants.DuplicateNames.RENAME
        )

        self.assertSequenceEqual(["Mary", "Mary_2", "Mary_3"], sut.tierNames)

    def test_tg_io_long_vs_short(self):
        """Tests reading of long vs short textgrids."""

        shortFN = join(self.dataRoot, "textgrid_to_merge.TextGrid")
        longFN = join(self.dataRoot, "textgrid_to_merge_longfile.TextGrid")

        self.assertTrue(areTheSameFiles(shortFN, longFN, textgrid.openTextgrid, True))

    def test_saving_short_textgrid(self):
        """Tests that short textgrid files are saved non-destructively."""
        fn = "textgrid_to_merge.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_short_file.textgrid")

        tg = textgrid.openTextgrid(shortFN, False)
        tg.save(outputFN, constants.TextgridFormats.SHORT_TEXTGRID, True)

        self.assertTrue(areTheSameFiles(shortFN, outputFN, readFile))

    def test_saving_long_textgrid(self):
        """Tests that long textgrid files are saved non-destructively."""
        fn = "textgrid_to_merge_longfile.TextGrid"
        longFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_long_file.textgrid")

        tg = textgrid.openTextgrid(longFN, False)
        tg.save(
            outputFN,
            format=constants.TextgridFormats.LONG_TEXTGRID,
            includeBlankSpaces=True,
        )

        self.assertTrue(areTheSameFiles(longFN, outputFN, readFile))

    def test_saving_and_loading_textgrid_json(self):
        """Tests that textgrid-like json files are saved non-destructively."""
        fn = "mary.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_textgrid_as_textgrid_json.json")
        outputLastFN = join(
            self.outputRoot, "saved_textgrid_as_json_then_textgrid.TextGrid"
        )

        tgFromTgFile = textgrid.openTextgrid(shortFN, False)
        tgFromTgFile.save(
            outputFN,
            format=constants.TextgridFormats.TEXTGRID_JSON,
            includeBlankSpaces=True,
        )

        tgFromJsonFile = textgrid.openTextgrid(outputFN, False)
        tgFromJsonFile.save(
            outputLastFN,
            format=constants.TextgridFormats.SHORT_TEXTGRID,
            includeBlankSpaces=True,
        )

        self.assertTrue(areTheSameFiles(shortFN, outputLastFN, readFile))

    def test_saving_and_loading_json(self):
        """Tests that json files are saved correctly."""
        fn = "mary.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "saved_textgrid_as_json.json")
        outputLastFN = join(
            self.outputRoot, "saved_textgrid_as_json_then_textgrid.TextGrid"
        )

        tgFromTgFile = textgrid.openTextgrid(shortFN, False)
        tgFromTgFile.save(
            outputFN,
            format=constants.TextgridFormats.JSON,
            includeBlankSpaces=True,
        )

        tgFromJsonFile = textgrid.openTextgrid(outputFN, False)
        tgFromJsonFile.save(
            outputLastFN,
            format=constants.TextgridFormats.SHORT_TEXTGRID,
            includeBlankSpaces=True,
        )

        self.assertTrue(areTheSameFiles(shortFN, outputLastFN, readFile))

    def test_saving_and_loading_json_leads_to_data_lose_in_one_edgecase(self):
        # Each tier can have a unique min and max timestamp
        # These timestamps can be different from the min and max specified for the file
        # The default json file maintains only a single min and max, so if the user has
        # different min and max timestamps in the tiers, that information will be lost
        fn = "mary_with_constrained_tier_times.TextGrid"
        shortFN = join(self.dataRoot, fn)
        outputFN = join(self.outputRoot, "mary_with_constrained_tier_times.json")

        tgFromTgFile = textgrid.openTextgrid(shortFN, False)
        tgFromTgFile.save(
            outputFN,
            format=constants.TextgridFormats.JSON,
            includeBlankSpaces=True,
            reportingMode="silence",
        )

        tgFromJsonFile = textgrid.openTextgrid(outputFN, False)

        # The timestamps in the source tg's tiers /don't/ match the source tg
        for tier in tgFromTgFile.tiers:
            self.assertNotEqual(tgFromTgFile.minTimestamp, tier.minTimestamp)
            self.assertNotEqual(tgFromTgFile.maxTimestamp, tier.maxTimestamp)

        # The timestamps in the json tg's tiers /do/ match the tg
        for tier in tgFromJsonFile.tiers:
            self.assertEqual(tgFromJsonFile.minTimestamp, tier.minTimestamp)
            self.assertEqual(tgFromJsonFile.minTimestamp, tier.minTimestamp)

    def test_save(self):
        userEntries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = [
            [0.0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = textgrid.IntervalTier("test", userEntries, 0, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg)

        self.assertEqual(expectedEntries, actualEntries)

    def test_save_with_minimum_time_stamp(self):
        userEntries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = [
            [0.3, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = textgrid.IntervalTier("test", userEntries, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg)

        self.assertEqual(expectedEntries, actualEntries)

    def test_save_with_force_zero_as_minimum_time(self):
        userEntries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = [
            [0, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = textgrid.IntervalTier("test", userEntries, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg, minTimestamp=0)

        self.assertEqual(expectedEntries, actualEntries)

    def test_save_with_force_larger_value_as_maximum_time(self):
        userEntries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = [
            [0.3, 0.4, ""],
            [0.4, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 3.0, ""],
        ]

        tier = textgrid.IntervalTier("test", userEntries, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg, maxTimestamp=3.0)

        self.assertEqual(expectedEntries, actualEntries)

    def test_save_with_force_too_small_minimum_time(self):
        # If you choose to force save to use a minTimestamp, all
        # of your entries must be higher than that minTimestamp
        userEntries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]

        tier = textgrid.IntervalTier("test", userEntries, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)

        with self.assertRaises(errors.ParsingError) as _:
            run_save(tg, minTimestamp=1.0)

    def test_save_with_minimum_interval_length(self):
        # The first entry will be stretched to fill the unlabeled region in
        # front of it: [0.30, 0.35, ''] (The unlabeled region starts at 0.3
        # instead of 0 because the minTimestamp for this tg is 0.3)
        userEntries = [[0.35, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = [
            [0.3, 0.6, "A"],
            [0.6, 0.8, ""],
            [0.8, 1.0, "E"],
            [1.0, 1.2, ""],
            [1.2, 1.3, "I"],
            [1.3, 2.0, ""],
        ]

        tier = textgrid.IntervalTier("test", userEntries, 0.3, 2.0)
        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg, minimumIntervalLength=0.06)

        self.assertEqual(expectedEntries, actualEntries)

    def test_save_with_ignore_blank_sections(self):
        """Tests that blank sections can be ignored on saving a textgrid."""
        entries = [[0.4, 0.6, "A"], [0.8, 1.0, "E"], [1.2, 1.3, "I"]]
        expectedEntries = entries  # Blank intervals should not be inserted
        tier = textgrid.IntervalTier("test", entries)

        tg = textgrid.Textgrid()
        tg.addTier(tier)
        actualEntries = run_save(tg, includeBlankSpaces=False)

        self.assertEqual(expectedEntries, actualEntries)


if __name__ == "__main__":
    unittest.main()
