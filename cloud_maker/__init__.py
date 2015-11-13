# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

VERSION_INFO = (0,8,2)
VERSION = '.'.join(str(x) for x in VERSION_INFO)

def version_check ():
    import cloud_maker.py_version.check
    return check()

if __name__ == '__main__':
    version_check()
    print("cloud-maker {}: Python version check succeeded.".format(VERSION))
