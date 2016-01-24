# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

import cloud_maker
import cloud_maker.py_version

cloud_maker.py_version.check()
print("cloud-maker {}: Python version check succeeded.".format(cloud_maker.VERSION))
