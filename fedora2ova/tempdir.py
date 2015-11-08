# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

import shutil
import tempfile

class TemporaryDirectory (object):
    basename = None
    _dir = None

    def __init__ (self, basename):
        self.basename = basename

    def __enter__ (self):
        self._dir = tempfile.mkdtemp(prefix=self.basename)
        return self._dir

    def __exit__ (self, type_, value, traceback):
        try:
            shutil.rmtree(self._dir)
        except:
            pass

