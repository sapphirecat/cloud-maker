# vim: fileencoding=utf-8
VERSION_INFO = (0,8,1)
VERSION = '.'.join(str(x) for x in VERSION_INFO)

def main (argv=None):
    from . import app
    return app.Provisioner().execute()
