# vim: fileencoding=utf-8
VERSION_INFO = (0,8,1)
VERSION = '.'.join(str(x) for x in VERSION_INFO)
ENV_SCOPE = 'FEDORA2OVA_'

def main ():
    from . import app
    return app.main()
