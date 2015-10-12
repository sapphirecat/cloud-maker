# vim: fileencoding=utf-8
# current status: direct port from perl
# which was pretty much a direct port of a shell script, IIRC
import argparse
import hashlib
import os
import os.path
import pathlib
import pkgutil
import re
from subprocess import call, check_call
import string
import sys
import tempfile
import time

VERSION = '0.5.1'; # SemVer

PROG = sys.argv[0]
ENV_SCOPE = 'FEDORA2OVA_'
VBOX_OS_TYPE = 'Fedora'
VBOX_CMD = 'VBoxManage'

unarchivers = ['xz', 'pxz', 'pixz']
line_pattern = re.compile(r"[\r\n]+")

if PROG == '-m':
    PROG = 'fedora2ova'


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
    print("{} version {}".format(os.path.basename(sys.argv[0]), VERSION), file=sys.stderr)
    if exit_code is not None:
        sys.exit(exit_code)


def get_env_default (basevar, def_val=None):
    return os.environ.get(ENV_SCOPE + basevar, def_val)

def write_file (name, content, encoding='utf-8'):
    with open(name, 'w') as f:
        f.write(content.encode(encoding))

def read_file (name, encoding='utf-8'):
    with open(name, 'r') as f:
        return f.read().decode(encoding)

def dir_create (path, mode=0o777, parents=True):
    p = pathlib.Path(path)
    if not p.exists(path):
        p.mkdir(mode=mode, parents=parents)

def splitlines (text):
    line_pattern.split(text)


def build_config_iso (tmpdir, host, keydata):
    host8 = host[0:8] if len(host) > 8 else host
    iso_name = os.path.join(tmpdir, host + "-config.iso")

    # Process a raw authorized_keys style file to YAML array.
    keylines = splitlines(keydata.strip())
    yaml_keys = "\n".join("\x20\x20- '{}'".format(x.replace("'", "''")) for x in keylines)

    # Build user-data files (to add SSH keys) and meta-data (hostname) files
    output = get_data('resources/user-data.yaml')
    write_file(os.path.join(tmpdir, 'user-data'),
               string.Template(output).substitute(dict(yaml_keys=yaml_keys)))

    output = get_data('resources/meta-data.yaml')
    write_file(os.path.joir(tmpdir, 'meta-data'),
               string.Template(output).substitute(dict(host=host, host8=host8)))

    # Create the ISO; xorriso needs to run within the ISO root dir!
    # [thus, cwd=tmpdir in Python]
    check_call(['xorriso', '-dev', iso_name,
                '-joliet', 'on', '-rockridge', 'on', '-volid', 'cidata',
                '-add', 'user-data', 'meta-data'],
               cwd=tmpdir)
    return iso_name


def unxz_image (filename):
    base = re.sub(r"\.xz$", '', filename, 1, re.I)
    if os.path.exists(base):
        raise ValueError("Can't unarchive {}: expected output {} exists".format(filename, base))

    for cmd in unarchivers:
        rc = call([cmd, '-d', filename])
        if rc != 0:
            continue

        # make sure file exists after successful decompression
        if not os.path.exists(base):
            raise RuntimeError("Unarchiver didn't produce expected name: {}".format(base))

        # return new filename
        return base

    raise RuntimeError("No working unarchiver found (any of: {})".format(unarchivers))

def build_vm (config_iso, vm_name=None, tmpdir=None, **opts):
    cloud_img = options.image
    # check for "stdin" all-lowercase with optional any-case ".xz" suffix...
    if re.match(r"^stdin(?i-msx:\.xz)?$", cloud_img):
        raise ValueError("Disk image named 'stdin' will confuse VBox")

    # decompress the image if it appears to be compressed
    if re.search(r"\.xz$", cloud_img, re.I):
        print("Decompressing cloud image...")
        cloud_img = unxz_image(cloud_img)

    cloud_img = pathlib.Path(cloud_img).resolve()

    # (re)convert the raw image to VDI
    vdi = cloud_img.parts[-1]
    vdi, changes = re.subn(r"\.raw\b", "vdi")
    if not changes:
        vdi += '.vdi'

    vdi = os.path.join(tmpdir, vdi)
    check_call([VBOX_CMD, 'convertfromraw', cloud_img, vdi, '--format', 'VDI'])

    try:
        # 1000 = basic sanity check that we have MB not GB.
        if options.imagesize and options.imagesize > 1000:
            check_call([VBOX_CMD, 'modifyhd', vdi, '--resize', options.imagesize])

        # create VM description and register it with VBox
        sha1 = hashlib.new('sha1')
        sha1.update("{}{}{}".format(os.getpid(), time.time(), random.random()).encode('utf-8'))
        vm_name += '_' + (sha1.hexdigest())[0:16]
        os_type = VBOX_OS_TYPE
        if not '32bit' in opts:
            os_type += '_64'
        check_call([VBOX_CMD, 'createvm', '--register', '--name', vm_name, '--ostype', os_type])

        # Settings:
        # * Enough RAM to avoid OOM issue seen at 512 MB (no swap on the image)
        # * Hardware clock in UTC (inexplicably NOT set correctly by --ostype)
        # * Disable unnecessary USB / Audio busses
        check_call([VBOX_CMD, 'modifyvm', vm_name,
                    '--memory', '768', '--vram', '16', '--rtcuseutc', 'on',
                    '--mouse', 'ps2', '--keyboard', 'ps2', '--usb', 'off', '--audio', 'none'])
        # allow access to the guest SSH
        check_call([VBOX_CMD, 'modifyvm', vm_name, '--nic1', 'nat',
                    '--natpf1', "ssh,tcp,127.0.0.1,{},,22".format(opts['sshport'])])

        # build a controller and connect our storage to it (all SATA/AHCI)
        check_call([VBOX_CMD, 'storagectl', vm_name, '--name', 'SATA',
                    '--add', 'sata', '--controller', 'IntelAhci',
                    '--portcount', '4', '--hostiocache', 'off', '--bootable', 'on'])
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
        raise RuntimeError('Improbably fast boot cycle: {.2f} sec.'.format(bootdelta))

    return vm_name


def export_vm (objdir, hostname, vm_name):
    filename = os.path.join(objdir, hostname + ".ova")
    check_call([VBOX_CMD, 'export', vm_name, '--output', filename])
    return filename


def cleanup_vm (vm_name):
    check_call([VBOX_CMD, 'unregistervm', '--delete', vm_name])


def build_arg_parser (prog=PROG):
    epi = string.Template(get_data("resources/epilog.txt")).substitute({
        'basename': prog,
        'var': ENV_SCOPE,
    })
    p = argparse.ArgumentParser(prog=prog, epilog=epi,
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       description="Convert a Fedora Cloud ISO to a VirtualBox OVA")
    p.add_argument('--version', action='version', version="%(prog)s {}".format(VERSION))
    p.add_argument('--32bit', '--32', default=get_env_default('32BIT', 0),
                   action='store_true',
                   help='Set the guest to 32-bit mode (for i686 cloud images.)')
    p.add_argument('--imagesize', '--imgsize', '--resize', '-s', type=int,
                   default=get_env_default('IMAGESIZE'),
                   help='Resize disk image to IMAGESIZE megabytes.')
    p.add_argument('--name', '-n', default=get_env_default('NAME', 'fedora'),
                   help='Hostname (and instance-id) to set.')
    p.add_argument('--objdir', '--outdir', '-o', default=get_env_default('OBJDIR', '.'),
                   help='Where to create final OVA.')
    p.add_argument('--pubkey', '--pub-key', '--public-key', '-k',
                   default=get_env_default('PUBKEY'),
                   help='SSH public key to authorize for the image\'s default user.')
    p.add_argument('--sshport', '--ssh-port', '-p', type=int,
                   default=get_env_default('SSHPORT', 18222),
                   help='Host port to be forwarded to the guest\'s SSH port.')
    p.add_argument('--tmpdir', '--tmp-dir', '-t',
                   default=get_env_default('TMPDIR'),
                   help='Where to create tempfiles and config ISO.')
    p.add_argument('image',
                   help='Path to the (possibly xz-compressed) Fedora Cloud image.')
    return p

def str_path (path):
    return str(pathlib.Path(path).resolve())

def check_options (options):
    if options.pubkey is None:
        usage(2, 'SSH public key must be provided with $'+ENV_SCOPE+'PUBKEY or --pubkey/-k flag')
    elif len(options.pubkey) < 1:
        usage(2, 'SSH public key path must not be empty')
    elif len(options.name) < 1:
        usage(3, 'Guest VM basename must not be empty')

    if not os.path.exists(options.image):
        usage(4, "Fedora Cloud image does not exist: {}".format(options.image))

    keydata = read_file(options.pubkey)
    if not len(keydata.strip()):
        # This is all the sanity checking I want to maintain on this.
        usage(2, 'Public key file found, but empty: ' + options.pubkey)

    ova_name = options.name + '.ova'
    if os.path.exists(ova_name):
        raise ValueError("{} exists; please move/delete it first".format(ova_name))
        sys.exit(5)

    options.objdir = str_path(options.objdir)

    if options.tmpdir is not None:
        options.tmpdir = str_path(options.tmpdir)

    if options.sshport and not (1024 <= options.sshport <= 65535):
        raise ValueError("SSH port must be between 1024 and 65535: {}".format(options.sshport))


def main_build (options):
    # build pipeline
    config_iso = build_config_iso(options.tmpdir, options.name, keydata)
    vm_id = build_vm(config_iso, options)
    ova_file = export_vm(options.objdir, options.name, vm_id)
    return ova_file

def main ():
    # command line processing
    options = build_arg_parser().parse_args()
    check_options(options)

    dir_create(options.objdir)
    if options.tmpdir is None:
        with tempfile.TemporaryDirectory(PROG) as d:
            options.tmpdir = d
            ova_file = main_build(options)
    else:
        dir_create(options.tmpdir)
        ova_file = main_build(options)

    if os.path.exists(ova_file):
        print("Completed: " + ova_file)
        cleanup_vm(vm_id)
    else:
        print("Seemed OK, but failed to create: " + ova_file, file=sys.stderr)
