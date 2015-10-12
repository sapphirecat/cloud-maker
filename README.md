# cloud-maker

Linux Cloud bootstrap scripts (Python version)

A successor to [fedora-pack](https://github.com/sapphirecat/fedora-pack), in a
language that isn’t so dead.

The main attraction is `make_provisioner`, which creates an image
bootstrapping script: given a directory and a script within, it generates a
single-file, self-extracting archive that unpacks the directory on the guest
and runs the configured script.

It’s designed for convenient use as a Packer shell provisioner, or a layer in
a Dockerfile.

# Changes from Fedora-Pack 0.7

Since the command line got unwieldy, cloud-maker’s `make_provisioner` uses a
configuration file instead.  It’s in the DOS/INI format that Python’s
configparser reads.  So you’ll write a config like
[provisioner.ini](provisioner.ini), defining at least one _system_ (one
machine or machine image) as a section, then use that section name to launch
the command:

    python -m make_provisioner main-debian

You can specify your own config file instead of using the default:

    python -m make_provisioner -c myconfig.ini webtier

Much of what the provisioner used to do has been **removed** in this version.
We do not pre-install any dependencies; since the script can be
system-specific, it can install _its own_ dependencies and launch a stage 3
script if it wants.  And now, `make_provisioner` can work out-of-the-box on
more systems and more base versions, since it knows a _lot_ less about them.

# Dependencies

The host requires **Python 3.2** and runs on any OS.

# Guest OS Support

`make_provisioner` is intended to run on any system with a POSIX /bin/sh,
including all popular Linux and BSD distros.  Please open an issue if it does
not.

# License

MIT.
