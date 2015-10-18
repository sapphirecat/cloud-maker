#!/usr/bin/env python
from __future__ import print_function, absolute_import, unicode_literals
import sys

_STATE = {'fail': False}

def perr (*args, **kwargs):
    _STATE['fail'] = True
    if 'file' not in kwargs:
        kwargs['file'] = sys.stderr
    return print(*args, **kwargs)

def check ():
    major, minor = sys.version_info[0:2]
    if major != 3:
        perr("Error: this is Python {}, not 3.x".format(major))
    elif minor < 2:
        perr("Error: this is Python 3.{}, not 3.2+".format(minor))
    if _STATE['fail']:
        perr("Python 3 (3.2+, less than 4.0) is required.")
        sys.exit(2)

if __name__ == '__main__':
    check()
    print("Python version check succeeded.")
