#!/usr/bin/env python
# encoding: utf-8
'''
Created on Aug 29, 2014

@author: tmahrt
'''
from setuptools import setup
import codecs
setup(name='praatio',
      version='3.3.3',
      author='Tim Mahrt',
      author_email='timmahrt@gmail.com',
      url='https://github.com/timmahrt/praatIO',
      package_dir={'praatio':'praatio'},
      packages=['praatio',
                'praatio.utilities'],
      package_data={'praatio': ['praatScripts/*.praat', ]},
      license='LICENSE',
      description='A library for working with praat and praat files *that comes with batteries included*',
      long_description=codecs.open('README.rst', 'r', encoding="utf-8").read(),
#       install_requires=[], # No requirements! # requires 'from setuptools import setup'
      )
