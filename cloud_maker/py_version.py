# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals
import sys

class VersionError (ValueError):
    pass

def check_ex ():
    major, minor = sys.version_info[0:2]
    if major == 3:
        if minor < 2:
            raise VersionError("Error: this is Python 3.{}, not 3.2+".format(minor))
    elif major == 2:
        if minor < 7:
            raise VersionError("Error: this is Python 2.{}, not 2.7".format(minor))
    else:
        raise VersionError("Error: this is Python {}, not 2.7 nor 3.x".format(major))

def check ():
    try:
        check_ex()
    except VersionError as e:
        print(e.args, file=sys.stderr)
        print("Python 2.7 or 3.2+ is required.", file=sys.stderr)
        sys.exit(2)
