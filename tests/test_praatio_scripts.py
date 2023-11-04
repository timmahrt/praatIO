import unittest
import os
from os.path import join
import shutil
from unittest.mock import patch
from typing import List
import sys

from tests.testing_utils import tempTextgrid

from praatio import textgrid
from praatio import praatio_scripts
from praatio.utilities.constants import Interval, Point, NameStyle
from praatio.utilities import errors

from tests.praatio_test_case import PraatioTestCase


class TestPraatioScriptsThatOutputFiles(PraatioTestCase):
    def __init__(self, *args, **kargs):
        super(TestPraatioScriptsThatOutputFiles, self).__init__(*args, **kargs)

        cwd = os.path.dirname(os.path.realpath(__file__))
        self.dataRoot = join(cwd, "files")
        self.outputRoot = join(self.dataRoot, "praatio_scripts_output")

    def setUp(self):
        if not os.path.exists(self.outputRoot):
            os.mkdir(self.outputRoot)

    def resetState(self):
        # For performance reasons, only empty the folder when strictly necessary
        # (instead of cleaning up in TearDown)
        if os.path.exists(self.outputRoot):
            shutil.rmtree(self.outputRoot)
            os.mkdir(self.outputRoot)

    def getOutputTextgrids(self) -> List[str]:
        return [fn for fn in os.listdir(self.outputRoot) if ".TextGrid" in fn]

    def getOutputWavs(self) -> List[str]:
        return [fn for fn in os.listdir(self.outputRoot) if ".wav" in fn]

    def test_split_audio_on_tier_throws_with_name_style_invalid_throws_exception(self):
        invalidNameStyle = "foo"
        with self.assertRaises(errors.WrongOption) as _:
            praatio_scripts.splitAudioOnTier(
                join(self.dataRoot, "bobby.wav"),
                join(self.dataRoot, "bobby.TextGrid"),
                "word",
                self.outputRoot,
                outputTGFlag=True,
                nameStyle=invalidNameStyle,
            )

    def test_split_audio_on_tier_return_fn_list_matches_output_wav_files(self):
        self.resetState()
        reportedWavs = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            nameStyle=NameStyle.NAME_AND_I_AND_LABEL,
        )
        reportedWavs = [fn for _, _, fn in reportedWavs]

        actualWavs = self.getOutputWavs()

        self.assertCountEqual(reportedWavs, actualWavs)

    def test_split_audio_on_tier_with_name_and_i_and_label_outputs_expected_filenames(
        self,
    ):
        sut = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            nameStyle=NameStyle.NAME_AND_I_AND_LABEL,
        )
        reportedWavs = [fn for _, _, fn in sut]

        self.assertEqual(4, len(reportedWavs))
        self.assertCountEqual(
            [
                "bobby_0_BOBBY.wav",
                "bobby_1_RIPPED.wav",
                "bobby_2_THE.wav",
                "bobby_3_LEDGER.wav",
            ],
            reportedWavs,
        )

    def test_split_audio_on_tier_with_name_and_label_outputs_expected_filenames(self):
        sut = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            nameStyle=NameStyle.NAME_AND_LABEL,
        )
        reportedWavs = [fn for _, _, fn in sut]

        self.assertEqual(4, len(reportedWavs))
        self.assertCountEqual(
            [
                "bobby_BOBBY.wav",
                "bobby_RIPPED.wav",
                "bobby_THE.wav",
                "bobby_LEDGER.wav",
            ],
            reportedWavs,
        )

    def test_split_audio_on_tier_with_name_and_i_outputs_expected_filenames(self):
        sut = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            nameStyle=NameStyle.NAME_AND_I,
        )
        reportedWavs = [fn for _, _, fn in sut]

        self.assertEqual(4, len(reportedWavs))
        self.assertCountEqual(
            [
                "bobby_0.wav",
                "bobby_1.wav",
                "bobby_2.wav",
                "bobby_3.wav",
            ],
            reportedWavs,
        )

    def test_split_audio_on_tier_with_label_outputs_expected_filenames(self):
        sut = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            nameStyle=NameStyle.LABEL,
        )
        reportedWavs = [fn for _, _, fn in sut]

        self.assertEqual(4, len(reportedWavs))
        self.assertCountEqual(
            [
                "BOBBY.wav",
                "RIPPED.wav",
                "THE.wav",
                "LEDGER.wav",
            ],
            reportedWavs,
        )

    @unittest.skipIf(sys.version_info < (3, 8), "Mocks changed in python 2.8")
    @patch("builtins.print")
    def test_split_audio_on_tier_with_label_prints_warning_when_duplicate_labels(
        self, mockStdout
    ):
        # splitAudioOnTier will print out when overwriting existing
        # values; to avoid this possibility, we reset the state
        self.resetState()

        # This textgrid has three labels that are duplicates of others
        tg = textgrid.Textgrid(0, 1.0)
        tier = textgrid.IntervalTier(
            "foo",
            [
                [0, 0.2, "hello"],
                [0.2, 0.4, "hello"],
                [0.4, 0.6, "world"],
                [0.6, 0.8, "world"],
                [0.8, 1.0, "world"],
            ],
        )
        tg.addTier(tier)

        with tempTextgrid(tg) as tgFd:
            # The uniqueness check is only run when
            # namestyle is 'label'
            praatio_scripts.splitAudioOnTier(
                join(self.dataRoot, "bobby.wav"),
                tgFd.name,
                "foo",
                self.outputRoot,
                nameStyle=NameStyle.LABEL,
            )

        self.assertEqual(1, len(mockStdout.mock_calls))
        for sut in mockStdout.mock_calls[0].args:
            self.assertEqual(
                sut,
                f"Overwriting wave files in: {self.outputRoot}\n"
                "Intervals exist with the same name:\nhello\nworld",
            )

    @patch("builtins.print")
    @unittest.skipIf(sys.version_info < (3, 8), "Mocks changed in python 2.8")
    def test_split_audio_on_tier_prints_warning_when_overwriting_content(
        self, mockStdout
    ):
        self.resetState()
        praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
        )
        self.assertEqual(0, len(mockStdout.mock_calls))

        praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
        )
        self.assertEqual(4, len(mockStdout.mock_calls))
        for sut in mockStdout.mock_calls[0].args:
            self.assertRegex(
                sut,
                f"Overwriting wave files in: {self.outputRoot}\n"
                "Files existed before or intervals exist with the same name:",
            )

    def test_split_audio_on_tier_wont_output_textgrids_if_asked(self):
        self.resetState()
        praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            outputTGFlag=False,
        )
        self.assertEqual(0, len(self.getOutputTextgrids()))

    def test_split_audio_on_tier_will_output_textgrids_if_asked(self):
        self.resetState()
        praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            outputTGFlag=True,
        )
        self.assertEqual(4, len(self.getOutputTextgrids()))

    def test_split_audio_without_allow_partial_intervals_is_more_strict_in_output(self):
        # This textgrid has three labels that are duplicates of others
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.6, "hello"],
                [0.6, 0.8, "world"],
            ],
        )
        auxTier = textgrid.IntervalTier(
            "bar",
            [
                [0.2, 0.4, "not included"],
                [0.4, 0.5, "included"],
                [0.7, 0.9, "also not included"],
            ],
        )

        tg.addTier(targetTier)
        tg.addTier(auxTier)

        with tempTextgrid(tg) as tgFd:
            # The uniqueness check is only run when
            # namestyle is 'label'
            praatio_scripts.splitAudioOnTier(
                join(self.dataRoot, "bobby.wav"),
                tgFd.name,
                "foo",
                self.outputRoot,
                nameStyle=NameStyle.LABEL,
                outputTGFlag=True,
                allowPartialIntervals=False,
            )

        sut1 = textgrid.openTextgrid(join(self.outputRoot, "hello.TextGrid"), False)
        sut1Entries = sut1.getTier("bar").entries
        self.assertEqual(1, len(sut1Entries))
        self.assertEqual(Interval(0, 0.1, "included"), sut1Entries[0])

        sut2 = textgrid.openTextgrid(join(self.outputRoot, "world.TextGrid"), False)
        sut2Entries = sut2.getTier("bar").entries
        self.assertEqual(0, len(sut2Entries))

    def test_split_audio_on_tier_with_custom_silence_label_skips_those_labels(self):
        sut = praatio_scripts.splitAudioOnTier(
            join(self.dataRoot, "bobby.wav"),
            join(self.dataRoot, "bobby.TextGrid"),
            "word",
            self.outputRoot,
            silenceLabel="RIPPED",
        )
        self.assertEqual(3, len(sut))


class TestSpellCheckEntries(PraatioTestCase):
    def spellcheck(self, x):
        return x in ["hello", "world"]

    def test_spell_check_entries_keeps_all_mispelled_words(self):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.6, "hello"],
                [0.6, 0.8, "wolrd"],
            ],
        )
        tg.addTier(targetTier)

        sut = praatio_scripts.spellCheckEntries(tg, "foo", "bar", self.spellcheck)

        expectedTier = textgrid.IntervalTier(
            "bar",
            [
                [0.6, 0.8, "wolrd"],
            ],
            0,
            1.0,
        )

        self.assertEqual(2, len(sut.tiers))
        self.assertEqual(expectedTier, sut.getTier("bar"))

    @patch("builtins.print")
    @unittest.skipIf(sys.version_info < (3, 8), "Mocks changed in python 2.8")
    def test_spell_check_entries_can_print_out_warnings(self, mockStdout):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.2, 0.4, "olleh"],
                [0.4, 0.6, "hello"],
                [0.6, 0.8, "wolrd"],
            ],
        )
        tg.addTier(targetTier)

        praatio_scripts.spellCheckEntries(
            tg, "foo", "bar", self.spellcheck, printEntries=True
        )
        self.assertEqual(2, len(mockStdout.mock_calls))
        for sut in mockStdout.mock_calls[0].args:
            self.assertEqual((0.2, 0.4, "olleh"), sut)
        for sut in mockStdout.mock_calls[1].args:
            self.assertEqual((0.6, 0.8, "wolrd"), sut)

    def test_spell_check_entries_splits_text_on_space(self):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.6, "olleh hello wolrd"],
            ],
        )
        tg.addTier(targetTier)

        sut = praatio_scripts.spellCheckEntries(tg, "foo", "bar", self.spellcheck)

        expectedTier = textgrid.IntervalTier(
            "bar",
            [
                [0.4, 0.6, "olleh, wolrd"],
            ],
            0,
            1.0,
        )

        self.assertEqual(2, len(sut.tiers))
        self.assertEqual(expectedTier, sut.getTier("bar"))

    def test_spell_check_entries_ignores_punctuation(self):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.6, "olleh; hello--wolrd?!"],
            ],
        )
        tg.addTier(targetTier)

        sut = praatio_scripts.spellCheckEntries(tg, "foo", "bar", self.spellcheck)

        expectedTier = textgrid.IntervalTier(
            "bar",
            [
                [0.4, 0.6, "olleh, wolrd"],
            ],
            0,
            1.0,
        )

        self.assertEqual(2, len(sut.tiers))
        self.assertEqual(expectedTier, sut.getTier("bar"))

    def test_spell_check_entries_throws_error_if_new_tier_name_exists_in_textgrid(self):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.6, "hello"],
                [0.6, 0.8, "wolrd"],
            ],
        )
        tg.addTier(targetTier)

        with self.assertRaises(errors.TierNameExistsError) as _:
            praatio_scripts.spellCheckEntries(tg, "foo", "foo", self.spellcheck)


class TestPraatioScriptsThatDontOutputFiles(PraatioTestCase):
    def test_split_tier_entries_will_append_a_new_tier_if_target_tier_name_is_novel(
        self,
    ):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.8, "hello world"],
            ],
        )
        tg.addTier(targetTier)

        sut = praatio_scripts.splitTierEntries(tg, "foo", "bar")

        expectedTier = textgrid.IntervalTier(
            "bar", [[0.4, 0.6, "hello"], [0.6, 0.8, "world"]], 0, 1.0
        )

        self.assertEqual(2, len(sut.tiers))
        self.assertEqual(expectedTier, sut.getTier("bar"))

    def test_split_tier_entries_raises_collision_error_when_overwriting_an_existing_entry(
        self,
    ):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.8, "hello world"],
            ],
        )
        auxTier = textgrid.IntervalTier(
            "bar",
            [
                [0.4, 0.5, "this will clash"],
            ],
        )

        tg.addTier(targetTier)
        tg.addTier(auxTier)

        with self.assertRaises(errors.CollisionError) as _:
            praatio_scripts.splitTierEntries(tg, "foo", "bar")

    def test_split_tier_entries_raises_collision_error_when_source_and_target_tier_are_same(
        self,
    ):
        tg = textgrid.Textgrid(0, 1.0)
        targetTier = textgrid.IntervalTier(
            "foo",
            [
                [0.4, 0.8, "hello world"],
            ],
        )
        tg.addTier(targetTier)

        with self.assertRaises(errors.CollisionError) as _:
            praatio_scripts.splitTierEntries(tg, "foo", "foo")


if __name__ == "__main__":
    unittest.main()
