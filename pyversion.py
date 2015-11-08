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
    if major == 3:
        if minor < 2:
            perr("Error: this is Python 3.{}, but not 3.2+".format(minor))
    elif major == 2:
        if minor < 7:
            perr("Error: this is Python 2.{}, but not 2.7+".format(minor))
    else:
        perr("Error: this is Python {}, not 2.x nor 3.x".format(major))

    if _STATE['fail']:
        perr("Python 2.7 or 3.2+ is required.")
        sys.exit(2)

if __name__ == '__main__':
    check()
    print("Python version check succeeded.")
