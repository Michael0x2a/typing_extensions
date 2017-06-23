#!/usr/bin/env python
# coding: utf-8

import sys
from distutils.core import setup

if sys.version_info < (2, 7, 0) or (3, 0, 0) <= sys.version_info < (3, 3, 0):
    sys.stderr.write('ERROR: You need Python 2.7 or 3.3+ '
                     'to install the typing package.\n')
    exit(1)

version = '3.6.1'
description = 'Type Hint backports for Python 3.5+'
long_description = '''\
Typing -- Type Hints for Python

This is a backport of the standard library typing module to Python
versions 3.5+. The typing module has seen several changes since it was
first added in Python 3.5.0, which means people who are using 3.5.0+
but are unable to upgrade to the latest version of Python are unable
to take advantage of some new features of the typing library, such as
typing.Type or typing.Coroutine.

This module allows those users to use the latest additions to the typing
module without worrying about naming conflicts with the standard library.
Users of Python 2.7, 3.3, and 3.4 should install the typing module
from pypi and use that directly, except when writing code that needs to
be compatible across multiple versions of Python.

Typing defines a standard notation for Python function and variable
type annotations. The notation can be used for documenting code in a
concise, standard format, and it has been designed to also be used by
static and runtime type checkers, static analyzers, IDEs and other
tools.
'''

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Python Software Foundation License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Software Development',
]

setup(name='typing_extensions',
      version=version,
      description=description,
      long_description=long_description,
      author='Guido van Rossum, Jukka Lehtosalo, Lukasz Langa',
      author_email='jukka.lehtosalo@iki.fi',
      url='https://docs.python.org/3/library/typing.html',
      license='PSF',
      keywords='typing function annotations type hints hinting checking '
               'checker typehints typehinting typechecking backport',
      py_modules=['typing_extensions'],
      classifiers=classifiers)
