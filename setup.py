# -*- coding: utf-8 -*-
# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages

with open('README.md') as f:
    __readme__ = f.read()

with open('LICENCE') as f:
    __license__ = f.read()

__version__ = "0.1dev"

setup(
    name='skycalc-ipy',
    version=__version__,
    description='Get atmospheric spectral information',
    long_description=__readme__,
    author='Kieran Leschinski',
    author_email='kieran.leschinski@univie.ac.at',
    url='https://github.com/astronomyk/skycalc_ipy',
    license=__license__,
    include_package_data=True,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=['requests', 'pyyaml', 'numpy', 'astropy']
    )
