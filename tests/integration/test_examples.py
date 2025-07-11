#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Jan 27, 2016

@author: tmahrt

Run user-facing example code.

The examples were all written as scripts.  They weren't meant to be
imported or run from other code.  So here, the integration test is just
importing the scripts, which causes them to execute.  If the code completes
with no errors, then the code is at least able to complete.

Testing whether or not the code actually did what it is supposed to is
another issue and will require some refactoring.
"""

import unittest
import os
import sys
from pathlib import Path

from tests.testing_utils import CoverageIgnoredTest

_root = os.path.join(Path(__file__).parents[2], "examples")
sys.path.append(_root)


# Ignoring test coverage because there is no validation in
# these tests other than "no unhandled exception occured"
# which is still important for the user-facing example code
class TestExamples(CoverageIgnoredTest):
    """Ensure example tests run without unhandled exceptions."""

    def test_add_tiers(self):
        """Run 'add_tiers.py'."""
        print(os.getcwd())
        import add_tiers

        print(os.getcwd())

    def test_anonymize_recordings(self):
        """Run 'anonymize_recording'."""
        import anonymize_recording

    def test_calculate_duration(self):
        """Run 'calculate_duration.py'."""
        print(os.getcwd())
        import calculate_duration

        print(os.getcwd())

    def test_correct_misaligned_tiers(self):
        """Run 'correct_misaligned_tiers.py'."""
        print(os.getcwd())
        import correct_misaligned_tiers

        print(os.getcwd())

    def test_delete_vowels(self):
        """Run 'delete_vowels.py'."""
        print(os.getcwd())
        import delete_vowels

        print(os.getcwd())

    def test_extract_subwavs(self):
        """Run 'extract_subwavs.py'."""
        print(os.listdir("."))
        import extract_subwavs

    def test_get_vowel_points(self):
        """Run 'get_vowel_points.py'."""
        import get_vowel_points

    def test_merge_adjacent_intervals(self):
        """Run 'merge_adjacent_intervals.py'."""
        import merge_adjacent_intervals

    def test_merge_tiers(self):
        """Run 'merge_tiers.py'."""
        print(os.getcwd())
        import merge_tiers

    def test_splice_example(self):
        """Run 'splice_example.py'."""
        import splice_example

    def test_split_audio_on_tier(self):
        """Run 'split_audio_on_tier.py'."""
        import split_audio_on_tier

    def test_textgrid_set_operations(self):
        """Run 'textgrid_set_operations.py'."""
        import textgrid_set_operations

    def setUp(self):
        unittest.TestCase.setUp(self)

        root = os.path.join(_root, "files")
        self.oldRoot = os.getcwd()
        os.chdir(_root)
        self.startingList = os.listdir(root)
        self.startingDir = os.getcwd()

    def tearDown(self):
        """Remove any files generated during the test."""
        # unittest.TestCase.tearDown(self)

        root = os.path.join(".", "files")
        endingList = os.listdir(root)
        rmList = [fn for fn in endingList if fn not in self.startingList]

        if self.oldRoot == root:
            for fn in rmList:
                fnFullPath = os.path.join(root, fn)
                if os.path.isdir(fnFullPath):
                    os.rmdir(fnFullPath)
                else:
                    os.remove(fnFullPath)

        os.chdir(self.oldRoot)


if __name__ == "__main__":
    unittest.main()
