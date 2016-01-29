#!/usr/bin/env python
# encoding: utf-8
'''
Created on Aug 29, 2014

@author: tmahrt
'''
from distutils.core import setup
setup(name='praatio',
      version='3.0.0',
      author='Tim Mahrt',
      author_email='timmahrt@gmail.com',
      package_dir={'praatio':'praatio'},
      packages=['praatio',
                'praatio.utilities'],
      package_data={'praatio': ['praatScripts/*.praat', ]},
      license='LICENSE',
      long_description=open('README.rst', 'r').read(),
#       install_requires=[], # No requirements! # requires 'from setuptools import setup'
      )