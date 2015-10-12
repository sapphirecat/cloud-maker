#!/bin/sh
set -e
self_file="$0"
export CLOUD_DIR=@CLOUD_DIR
sudo install -d -m 0700 -o "`id -u`" -g "`id -g`" "${CLOUD_DIR}"
tail -n +@CUT_LINE "${self_file}" | gzip -dc - | tar xp -C "${CLOUD_DIR}" -f -
cd "${CLOUD_DIR}"
exec @RUNNER
