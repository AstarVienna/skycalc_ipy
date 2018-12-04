# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages
from skycalc_ipy.version import __version__

with open('README.md') as f:
    readme = f.read()

with open('LICENCE') as f:
    license = f.read()


setup(
    name='skycalc_ipy',
    version=__version__,
    description='Get atmospheric spectral information',
    long_description=readme,
    author='Kieran Leschinski',
    author_email='kieran.leschinski@univie.ac.at',
    url='https://github.com/astronomyk/skycalc_ipy',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
    # packages=find_packages()
)

