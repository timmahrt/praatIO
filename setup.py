'''
Created on Aug 29, 2014

@author: tmahrt
'''
from distutils.core import setup
setup(name='pyPraat',
      version='1.0.0',
      author='Tim Mahrt',
      author_email='timmahrt@gmail.com',
      package_dir={'pypraat':'src'},
      packages=['pypraat'],
      license='LICENSE',
      long_description=open('README.txt', 'r').read(),
#       install_requires=[], # No requirements! # requires 'from setuptools import setup'
      )