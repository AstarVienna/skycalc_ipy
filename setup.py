# -*- coding: utf-8 -*-
# Learn more: https://github.com/kennethreitz/setup.py
"""
Skycalc_ipy - a python wrapper for the ESO skycalc server
=========================================================

    $ pip install wheel twine

How to compile and put these on pip::

    $ python setup.py sdist bdist_wheel
    $ twine upload dist/*

Errors
------

- 'long_description_content_type not found':
  Can occur because the licence string is too long.
  Consider just referencing the GNU licences rather than including the full
  thing in the licence section.

"""



from setuptools import setup, find_packages

with open('skycalc_ipy/version.py') as f:
    __version__ = f.readline().split("'")[1]

with open('README.md') as f:
    __readme__ = f.read()

with open('LICENCE') as f:
    __license__ = f.read()


setup(
    name='skycalc-ipy',
    version=__version__,
    description='Get atmospheric spectral information from the ESO skycalc server',
    long_description_content_type="text/markdown",
    long_description=__readme__,
    author='Kieran Leschinski',
    author_email='kieran.leschinski@univie.ac.at',
    url='https://github.com/AstarVienna/skycalc_ipy',
    license=__license__,
    include_package_data=True,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=['requests', 'pyyaml', 'numpy', 'astropy']
    )
