# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

from . import VERSION
from .data import get_data
from .template import Template

from argparse import ArgumentParser
from codecs import open
try:
    import configparser
    _CONFIG_PARSER = configparser.ConfigParser
except ImportError:
    import ConfigParser as configparser
    _CONFIG_PARSER = configparser.SafeConfigParser
import os
import os.path
import platform
import posixpath
import shutil
import sys
import tarfile
import tempfile
import traceback

def _first_key (d, keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default

def shquote (s):
    return "\\'".join("'" + p + "'" for p in s.split("'"))

class Provisioner (object):
    PROG = 'make_provisioner'
    config = None
    options = None
    handlers = None

    def parse_args (self, args, prog):
        desc = "Creates a shell provisioner for guest machines"
        p = ArgumentParser(prog=prog, description=desc)
        p.add_argument('--version', action='version',
                       version="%(prog)s {}".format(VERSION))
        # why doesn't argparse put the default in the output?
        p.add_argument('--config', '-c', metavar='FILE', default='provisioner.ini',
                       help='Read configuration of systems from FILE (provisioner.ini)')
        p.add_argument('--output', '-o', metavar='FILE',
                       help='Write the resulting provisioner to the given FILE (config file\'s "output_file" option)')
        p.add_argument('system', metavar='SYSTEM',
                       help='Create the provisioner for the SYSTEM listed in the configuration file')
        self.options = p.parse_args(args)

    def execute (self, args=sys.argv[1:]):
        self.parse_args(args, self.PROG)
        self.read_config(self.options.system, self.options.config)

        conf = self.config
        output = self.options.output
        if output is None:
            try:
                output = conf['output_file']
            except KeyError:
                output = 'provisioner.sh'
        self.create_provisioner(output, conf['stage2_dir'])
        return 0

    def read_config (self, system, path, encoding='utf-8'):
        default = configparser.DEFAULTSECT
        ini = _CONFIG_PARSER() # ConfigParser [py3] or SafeConfigParser [py2]
        ini.optionxform = lambda o: o
        with open(path, 'r', encoding=encoding) as fp:
            try:
                ini.read_file(fp, path)
            except AttributeError:
                ini.readfp(fp, path)

        # set defaults from the environment
        if not ini.has_option(default, 'HOME'):
            ini.set(default, 'HOME', os.path.expanduser("~"))
        if not ini.has_option(default, 'USER'):
            ini.set(default, 'USER', _first_key(os.environ, ("USER", "USERNAME", "LOGNAME"), ''))

        # make a dictionary interface to the config because I like it.
        # the difference: this version resolves HOME/USER now, not later.
        # so if you're extending this, beware of that, I guess :-/
        self.config = dict(ini.items(system))

    def get_sfx_stub (self):
        txt = get_data('scripts/guest.sh').decode('utf-8')

        # I would check that RUNNER would not be '../../pwnx0r', but the
        # provisioner could just be "exec /var/pwnx0r" instead.  Without this.
        conf = self.config
        d = {"CUT_LINE": 1 + txt.count("\n"),
             "CLOUD_DIR": shquote(conf.get("guest_stage2_dir", "/var/tmp/cloud-maker")),
             "RUNNER": shquote('./' + conf.get("stage2_script", "main.sh")),
            }

        return Template(txt).substitute(d)

    def build_tar (self, fp, rootdir):
        # If we're not on Windows, rely on the host's executable bits.
        # Otherwise, split off for a massive hack.
        tar = tarfile.open(mode='w:gz', fileobj=fp, compresslevel=9)
        try:
            if platform.system() == 'Windows':
                self._build_tar_win(fp, rootdir, tar)
            else:
                self._build_tar_posix(fp, rootdir, tar)
        finally:
            tar.close()

    def _posixify (self, os_path):
        # danger: don't pass absolute OS paths through here, only dir-relative
        # ones. POSIX won't find "c:\\/Users/alice/..."
        rseg = []
        while True:
            bit = os.path.split(os_path)
            rseg.append(bit[1])
            if not bit[0]:
                break
            os_path = bit[0]

        rseg.reverse()
        return posixpath.join(*rseg)

    def _build_tar_win (self, fp, rootdir, tar):
        # Python's archive builders don't set anything executable inside the
        # archive on Windows, which the guest needs.  We set the x-bit inside
        # the archive based on whether the file 'looks executable' (begins
        # with a shebang, or ELF magic.)
        #
        # We can't use tar.add() with a filter, because the TarInfo doesn't
        # have the external path to examine. Nor does it generate names
        # relative to the root.  We don't want to pack things as
        # "/Users/betty/provisioner/aws/stage2.sh"...
        for container, dirs, files in os.walk(rootdir):
            tar_dir = self._posixify(os.path.relpath(container, rootdir))
            for dname in dirs:
                # abs_name: fully-qualified host OS path
                # tar_dir: in-tar dirname (always POSIX)
                abs_name = os.path.join(container, dname)
                fi = tar.gettarinfo(abs_name, posixpath.join(tar_dir, dname))
                fi.mode &= 0o755
                tar.addfile(fi)

            for fname in files:
                abs_name = os.path.join(container, fname)
                fi = tar.gettarinfo(abs_name, posixpath.join(tar_dir, fname))
                fi.mode &= 0o0755
                with open(abs_name, 'rb') as magic:
                    zero = magic.tell()
                    try:
                        m4 = magic.read(4)
                        if m4.startswith(b'#!') or m4 == b'\x7fELF':
                            fi.mode |= 0o111
                    except Exception as e:
                        print("exec hack for " + abs_name + ": " + str(e))
                    finally:
                        magic.seek(zero, 0)
                    # add fully-constructed fileinfo to archive
                    tar.addfile(fi, magic)

    def _build_tar_posix (self, fp, rootdir, tar):
        # a stripped-down _build_tar_win(), see there for detail
        for container, dirs, files in os.walk(rootdir):
            tar_dir = self._posixify(os.path.relpath(container, rootdir))
            for fname in files:
                abs_name = os.path.join(container, fname)
                tar.add(abs_name, arcname=posixpath.join(tar_dir, fname))

    def create_provisioner (self, out_file, stage2_dir):
        with open(out_file, 'wb') as sfx:
            # write the SFX stub to the provisioner
            sfx.write(self.get_sfx_stub().encode('utf-8'))

            # create the tmpfile for the payload archive to be attached
            with tempfile.TemporaryFile() as tgz:
                # tarfile can't write into a non-zero position
                zero = tgz.tell()
                self.build_tar(tgz, stage2_dir)
                tgz.seek(zero, 0)
                shutil.copyfileobj(tgz, sfx)

def main ():
    try:
        return Provisioner().execute()
    except:
        traceback.print_exc()
        return 2
