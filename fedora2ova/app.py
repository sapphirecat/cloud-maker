# vim: fileencoding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

# current status: direct port from perl
# which was a port of a shell script, I think
import argparse
from codecs import open
import hashlib
import os
import os.path
import pkgutil
import random
import re
from subprocess import call, check_call
import string
import sys
import tempfile
import time
import traceback

from . import VERSION, ENV_SCOPE

PROG = 'fedora2ova'
VBOX_OS_TYPE = 'Fedora'
VBOX_CMD = 'VBoxManage'

unarchivers = ['xz', 'pxz', 'pixz']
line_pattern = re.compile(r"[\r\n]+")

try:
    TemporaryDirectory = tempfile.TemporaryDirectory
except AttributeError:
    from . import tempdir
    TemporaryDirectory = tempdir.TemporaryDirectory



def get_data (filename, encoding='utf-8'):
    bits = pkgutil.get_data(__name__, filename)
    if encoding is not None:
        return bits.decode(encoding)
    else:
        return bits

def usage (exit_code=2, message=None):
    f = sys.stderr
    if exit_code == 0:
        version()
        f = sys.stdout
    elif message is not None:
        print(message, file=f)
        print("", file=f)

    tvars = dict(
        var = ENV_SCOPE,
        basename = os.path.basename(sys.argv[0])
    )
    text = get_data("resources/usage.txt")
    print(string.Template(text).substitute(tvars), file=f, end="")
    sys.exit(exit_code)

def version (exit_code=None):
    print("{} version {}".format(os.path.basename(sys.argv[0]), VERSION),
          file=sys.stderr)
    if exit_code is not None:
        sys.exit(exit_code)


def get_env_default (basevar, def_val=None):
    return os.environ.get(ENV_SCOPE + basevar, def_val)

def write_file (name, content, encoding='utf-8'):
    with open(name, 'w', encoding=encoding) as f:
        f.write(content)

def read_file (name, encoding='utf-8'):
    with open(name, 'r', encoding=encoding) as f:
        return f.read()

def dir_create (path, mode=0o777, parents=True):
    if not os.path.exists(path):
        if parents:
            os.makedirs(path, mode)
        else:
            os.mkdir(path, mode)

def splitlines (text):
    return line_pattern.split(text)


def build_config_iso (tmpdir, host, keydata):
    host8 = host[0:8] if len(host) > 8 else host
    iso_name = os.path.join(tmpdir, host + "-config.iso")

    # Process a raw authorized_keys style file to YAML array.
    keylines = splitlines(keydata.strip())
    yaml_keys = "\n".join("\x20\x20- '{}'".format(x.replace("'", "''"))
                          for x in keylines)

    # Build user-data files (to add SSH keys) and meta-data (hostname) files
    output = get_data('resources/user-data.yaml')
    write_file(os.path.join(tmpdir, 'user-data'),
               string.Template(output).substitute(dict(yaml_keys=yaml_keys)))

    output = get_data('resources/meta-data.yaml')
    tpl_vars = dict(host=host, host8=host8)
    write_file(os.path.join(tmpdir, 'meta-data'),
               string.Template(output).substitute(tpl_vars))

    # Create the ISO; xorriso needs to run within the ISO root dir!
    # [thus, cwd=tmpdir in Python]
    # xorriso will warn about volid's format, but cloud-config might require
    # this *specific* name (they include it without comment in examples)
    check_call(['xorriso', '-dev', iso_name,
                '-joliet', 'on', '-rockridge', 'on', '-volid', 'cidata',
                '-add', 'user-data', 'meta-data'],
               cwd=tmpdir)
    return iso_name


def unxz_image (filename):
    base = re.sub(r"\.xz$", '', filename, 1, re.I)
    if os.path.exists(base):
        err = "Can't unarchive {}: expected output {} exists"
        raise ValueError(err.format(filename, base))

    for cmd in unarchivers:
        rc = call([cmd, '-d', filename])
        if rc != 0:
            continue

        # make sure file exists after successful decompression
        if not os.path.exists(base):
            err = "Unarchiver didn't produce expected name: {}"
            raise RuntimeError(err.format(base))

        # return new filename
        return base

    err = "No working unarchiver found (any of: {})"
    raise RuntimeError(err.format(unarchivers))

def build_vm (config_iso, options):
    cloud_img = options.image
    vm_name = options.name
    tmpdir = options.tmpdir
    # check for "stdin" all-lowercase with optional any-case ".xz" suffix...
    if re.match(r"^stdin(?:(?i)\.xz)?$", cloud_img):
        raise ValueError("Disk image named 'stdin' will confuse VirtualBox")

    # decompress the image if it appears to be compressed
    if re.search(r"\.xz$", cloud_img, re.I):
        print("Decompressing cloud image...")
        cloud_img = unxz_image(cloud_img)

    cloud_img = os.path.abspath(cloud_img)

    # (re)convert the raw image to VDI
    vdi = os.path.basename(cloud_img)
    vdi, changes = re.subn(r"\.raw\b", ".vdi", vdi)
    if not changes:
        vdi += '.vdi'

    vdi = os.path.join(tmpdir, vdi)
    check_call([VBOX_CMD, 'convertfromraw', str(cloud_img), vdi,
                '--format', 'VDI'])

    try:
        # 1000 = basic sanity check that we have MB not GB.
        if options.imagesize and options.imagesize > 1000:
            check_call([VBOX_CMD, 'modifyhd', vdi,
                        '--resize', str(options.imagesize)])

        # create VM description and register it with VBox
        sha1 = hashlib.new('sha1')
        sha1.update("{}{}{}".format(os.getpid(),
                                    time.time(),
                                    random.random()
                                   ).encode('utf-8'))
        vm_name += '_' + (sha1.hexdigest())[0:16]
        os_type = VBOX_OS_TYPE
        if not getattr(options, '32bit'):
            os_type += '_64'
        check_call([VBOX_CMD, 'createvm', '--register',
                    '--name', vm_name,
                    '--ostype', os_type])

        # Settings:
        # * Enough RAM to avoid OOM issue seen at 512 MB (no swap on the image)
        # * Hardware clock in UTC (inexplicably NOT set correctly by --ostype)
        # * Disable unnecessary USB / Audio busses
        check_call([VBOX_CMD, 'modifyvm', vm_name,
                    '--memory', '768', '--vram', '32', '--rtcuseutc', 'on',
                    '--mouse', 'ps2', '--keyboard', 'ps2',
                    '--usb', 'off', '--audio', 'none'])
        # allow access to the guest SSH
        port_fwd = "ssh,tcp,127.0.0.1,{},,22".format(options.sshport)
        check_call([VBOX_CMD, 'modifyvm', vm_name,
                    '--nic1', 'nat', '--natpf1', port_fwd])

        # build a controller and connect our storage to it (all SATA/AHCI)
        check_call([VBOX_CMD, 'storagectl', vm_name, '--name', 'SATA',
                    '--add', 'sata', '--controller', 'IntelAhci',
                    '--portcount', '4', '--hostiocache', 'off',
                    '--bootable', 'on'])
        check_call([VBOX_CMD, 'storageattach', vm_name, '--storagectl', 'SATA',
                    '--port', '0', '--type', 'hdd', '--medium', vdi])
    except BaseException:
        call([VBOX_CMD, 'closemedium', vdi ]) # clean up zombie VDI
        raise

    check_call([VBOX_CMD, 'storageattach', vm_name, '--storagectl', 'SATA',
                '--port', '3', '--type', 'dvddrive', '--medium', config_iso ])

    # It turns out VBox can fail and return exit code zero.
    # We'd better make sure it's plausible that the VM booted.
    bootstart = time.time()
    check_call(['VBoxHeadless', '-s', vm_name ])
    bootdelta = time.time() - bootstart

    # Approximately "the amount of time vbox spends on the pre-boot screen",
    # so that even if the cloud image gets near-instant, this stays accurate.
    if bootdelta < 2.0:
        err = 'Improbably fast boot cycle: {.2f} sec.'
        raise RuntimeError(err.format(bootdelta))

    return vm_name


def export_vm (objdir, hostname, vm_name):
    filename = os.path.join(objdir, hostname + ".ova")
    check_call([VBOX_CMD, 'export', vm_name, '--output', filename])
    return filename


def cleanup_vm (vm_name):
    check_call([VBOX_CMD, 'unregistervm', '--delete', vm_name])


def build_arg_parser (prog=PROG):
    default_pk = os.path.expanduser('~/.ssh/id_rsa.pub')
    epi = string.Template(get_data("resources/epilog.txt")).substitute({
        'basename': prog,
        'var': ENV_SCOPE,
    })
    # some contortions to fit 80 columns of width
    new = dict(prog=prog, epilog=epi,
               formatter_class=argparse.RawDescriptionHelpFormatter,
               description="Convert a Fedora Cloud ISO to a VirtualBox OVA"
              )
    htxt = {
        '32': 'Set the guest to 32-bit mode (for i686 cloud images.)',
        'size': 'Resize disk image to IMAGESIZE megabytes.',
        'name': 'Hostname (and instance-id) to set.',
        'objdir': 'Where to create final OVA.',
        'key': 'SSH public key to authorize for the image\'s default user.',
        'port': 'Host port to be forwarded to the guest\'s SSH port.',
        'tmp': 'Where to create tempfiles and config ISO.',
        'image': 'Path to the (possibly xz-compressed) Fedora Cloud image.',
    }
    p = argparse.ArgumentParser(**new)
    p.add_argument('--version', action='version',
                   version="%(prog)s {}".format(VERSION))
    p.add_argument('--32bit', '--32', action='store_true',
                   help=htxt['32'], default=get_env_default('32BIT', 0))
    p.add_argument('--imagesize', '--imgsize', '--resize', '-s', type=int,
                   help=htxt['size'], default=get_env_default('IMAGESIZE'))
    p.add_argument('--name', '-n', default=get_env_default('NAME', 'fedora'),
                   help=htxt['name'])
    p.add_argument('--objdir', '--outdir', '-o',
                   help=htxt['objdir'],
                   default=get_env_default('OBJDIR', '.'))
    p.add_argument('--pubkey', '--pub-key', '--public-key', '-k',
                   help=htxt['key'],
                   default=get_env_default('PUBKEY', default_pk))
    p.add_argument('--sshport', '--ssh-port', '-p', type=int,
                   help=htxt['port'],
                   default=get_env_default('SSHPORT', 18222))
    p.add_argument('--tmpdir', '--tmp-dir', '-t',
                   help=htxt['tmp'],
                   default=get_env_default('TMPDIR'))
    p.add_argument('image',
                   help=htxt['image'])
    return p

def str_path (path):
    return os.path.abspath(path)

def check_options (options):
    if options.pubkey is None:
        usage(2, 'SSH public key must be provided with $' + ENV_SCOPE +
              'PUBKEY or --pubkey/-k flag')
    elif len(options.pubkey) < 1:
        usage(2, 'SSH public key path must not be empty')
    elif not os.path.exists(options.pubkey):
        usage(2, 'SSH public key file not found')
    elif len(options.name) < 1:
        usage(3, 'Guest VM basename must not be empty')

    if not os.path.exists(options.image):
        usage(4, "Fedora Cloud image does not exist: {}".format(options.image))

    try:
        keydata = read_file(options.pubkey)
    except OSError as e:
        usage(2, 'Public key file is not accessible: {}'.format(e.message))
    if not len(keydata.strip()):
        # This is all the sanity checking I want to maintain on this.
        usage(2, 'Public key file found, but empty: {}'.format(options.pubkey))
    options.pubkey_data = keydata

    ova_name = options.name + '.ova'
    if os.path.exists(ova_name):
        err = "{} exists; please move/delete it first"
        raise ValueError(err.format(ova_name))
        sys.exit(5)

    options.objdir = str_path(options.objdir)

    if options.tmpdir is not None:
        options.tmpdir = str_path(options.tmpdir)

    if options.sshport and not (1024 <= options.sshport <= 65535):
        err = "SSH port must be between 1024 and 65535: {}"
        raise ValueError(err.format(options.sshport))


def main_build (options):
    # build pipeline
    config_iso = build_config_iso(options.tmpdir,
                                  options.name,
                                  options.pubkey_data)
    vm_id = build_vm(config_iso, options)
    ova_file = export_vm(options.objdir, options.name, vm_id)
    return vm_id, ova_file

def post_build (vm_id, ova_file):
    # post-build checks; refactored because VBox unregistervm fails when the
    # temporary directory housing the config ISO has been deleted.
    if os.path.exists(ova_file):
        print("Completed: " + ova_file)
        cleanup_vm(vm_id)
    else:
        print("Seemed OK, but failed to create: " + ova_file, file=sys.stderr)

def main_with_options (options):
    check_options(options)

    dir_create(options.objdir)
    if options.tmpdir is None:
        realprog = PROG
        if realprog.startswith('-') or realprog.startswith('.'):
            realprog = '_' + realprog
        with TemporaryDirectory(realprog) as d:
            options.tmpdir = d
            vm_id, ova_file = main_build(options)
            post_build(vm_id, ova_file)
    else:
        dir_create(options.tmpdir)
        vm_id, ova_file = main_build(options)
        post_build(vm_id, ova_file)

def main ():
    try:
        main_with_options(build_arg_parser().parse_args())
        return 0
    except:
        traceback.print_exc()
        return 2
