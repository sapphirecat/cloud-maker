# vim: fileencoding=utf-8
import pkgutil

def get_data(name):
    return pkgutil.get_data(__name__, name)
