import string

class Template (string.Template):
    delimiter = '@'
    escaped = '@@'
