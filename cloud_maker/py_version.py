# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals
import sys

class VersionError (ValueError):
    pass

def check_ex ():
    v = sys.version_info
    if v.major == 3:
        if v.minor < 3 or (v.minor == 3 and v.micro < 4):
            raise VersionError("Error: this is Python 3.{}.{}, not 3.3.4+".format(v.minor, v.micro))
    elif v.major == 2:
        if v.minor < 7:
            raise VersionError("Error: this is Python 2.{}, not 2.7".format(v.minor))
    else:
        raise VersionError("Error: this is Python {}, not 2.7 nor 3.x".format(v.major))

def check ():
    try:
        check_ex()
    except VersionError as e:
        print(e.args[0], file=sys.stderr)
        print("Python 2.7.x or 3.3.4+ is required.", file=sys.stderr)
        sys.exit(2)
