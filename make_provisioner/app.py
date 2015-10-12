from .data import get_data
from .template import Template

from argparse import ArgumentParser
import configparser
import os
import pathlib
import platform
import shutil
import sys
import tarfile
import tempfile

def _first_key (d, keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default

def shquote (s):
    return "\\'".join("'" + p + "'" for p in s.split("'"))

class Provisioner (object):
    config = None
    options = None
    handlers = None

    def parse_args (self, args, prog):
        desc = "Creates a shell provisioner for guest machines"
        p = ArgumentParser(prog=prog, description=desc)
        # why doesn't argparse put the default in the output?
        p.add_argument('--config', '-c', metavar='FILE', default='provisioner.ini',
                       help='Read configuration of systems from FILE (provisioner.ini)')
        p.add_argument('--output', '-o', metavar='FILE',
                       help='Write the resulting provisioner to the given FILE (config file\'s "output_file" option)')
        p.add_argument('system', metavar='SYSTEM',
                       help='Create the provisioner for the SYSTEM listed in the configuration file')
        self.options = p.parse_args(args)

    def execute (self, args=sys.argv[1:], prog=sys.argv[0]):
        self.parse_args(args, prog)
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
        ini = configparser.ConfigParser()
        ini.optionxform = lambda o: o
        with open(path, 'rt', encoding=encoding) as fp:
            ini.read_file(fp, path)

        # set defaults from the environment
        d = ini[configparser.DEFAULTSECT]
        if "HOME" not in d:
            d["HOME"] = os.path.expanduser("~")
        if "USER" not in d:
            d["USER"] = _first_key(os.environ, ("USER", "USERNAME", "LOGNAME"), '')

        self.config = ini[system]

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
            if platform.system() != 'Windows':
                tar.add(rootdir)
            else:
                self._build_tar_win(fp, rootdir, tar)
        finally:
            tar.close()

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
            tar_dir = os.path.relpath(container, rootdir)
            if tar_dir == '.':
                tar_dir = ''
            for dname in dirs:
                abs_name = os.path.join(container, fname)
                path = pathlib.PurePosixPath(tar_dir, fname)
                fi = tar.gettarinfo(abs_name, str(path))
                fi.mode &= 0o755
                tar.addfile(fi)

            for fname in files:
                abs_name = os.path.join(container, fname)
                path = pathlib.PurePosixPath(tar_dir, fname)
                fi = tar.gettarinfo(abs_name, str(path))
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
