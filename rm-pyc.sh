#!/bin/sh
set -e
find . -type f -name '*.pyc' -exec rm '{}' \;
find . -type d -name __pycache__ -print0 | xargs -r0 rm -r
