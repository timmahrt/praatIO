#!/usr/bin/env python
# encoding: utf-8
"""
Created on Aug 29, 2014

@author: tmahrt
"""
from setuptools import setup
import io

setup(
    name="praatio",
    python_requires=">3.6.0",
    version="5.0.0",
    author="Tim Mahrt",
    author_email="timmahrt@gmail.com",
    url="https://github.com/timmahrt/praatIO",
    package_dir={"praatio": "praatio"},
    packages=["praatio", "praatio.utilities", "praatio.data_classes"],
    package_data={
        "praatio": [
            "praatScripts/*.praat",
        ]
    },
    install_requires=[
        "typing_extensions",
    ],
    license="LICENSE",
    description=(
        "A library for working with praat, textgrids, "
        "time aligned audio transcripts, and audio files."
    ),
    long_description=io.open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
)
