# vim: fileencoding=utf-8
import string

class Template (string.Template):
    delimiter = '@'
    escaped = '@@'
