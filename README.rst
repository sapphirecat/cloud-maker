===========
cloud-maker
===========

Linux Cloud bootstrap scripts (Python 3 version)

A successor to fedora-pack_, in a language that isn’t so dead.

The main attraction is ``make_provisioner``, which creates an image
bootstrapping script: given a directory and a script within, it generates a
single-file, self-extracting archive that unpacks the directory on the guest
and runs the configured script.

It’s designed for convenient use as a Packer shell provisioner, or a layer in
a Dockerfile.

There’s another script, ``fedora2ova``, which converts a (possibly
xz-compressed) Fedora Cloud raw disk image into a VirtualBox OVA using the
VBoxManage tool.

Changes from Fedora-Pack 0.7
----------------------------

As noted in the description, this version uses **Python 3.2+** instead of Perl
to do all the work.

Distros and Versions are gone
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Much of what the provisioner used to do has been **removed** in this version.
We do not pre-install any dependencies; since the script can be
system-specific, it can install *its own* dependencies and launch a stage 3
script if it wants.  And now, ``make_provisioner`` works as-is on many more
systems and versions, since it knows *very little* about them.

Cautionary note for Windows hosts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your stage2 script may fail to start with ‘no such file or directory’ or
possibly ‘bad interpreter’ if you accidentally save it with CRLF line-endings.
In vim, be sure to use ``:set ff=unix`` to change the ``fileformat``.

Byzantine command-line replaced with config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

cloud-maker’s ``make_provisioner`` uses a configuration file instead of
specifying everything on the command-line.  It’s in the DOS/INI format that
Python’s configparser reads.  So you’ll write a config like
provisioner.ini_, defining at least one *system* (one machine or machine
image) as a section, then use that section name to launch the command:

    ``python -m make_provisioner main-debian``

You can specify your own config file instead of using the default:

    ``python -m make_provisioner -c myconfig.ini webtier``

Dependencies
------------

The host requires **Python 3.2** and runs on any OS.

Mac OS X users with Homebrew can use ``brew install python3`` to get the
``python3`` command.  Many Linux distros also provide ``python3`` packages, and of
course, Python_ itself has installers for each OS.  (I sacrificed “no extra
downloads” a little, to reduce future maintenance effort.)

* ``make_provisioner`` has no further dependencies.
* ``fedora2ova`` requires the Fedora Cloud raw image, ``xorriso``, and VirtualBox
  management tools (``VBoxManage``).  It must run on a host that supports
  running Fedora as a VirtualBox guest in order for the guest’s cloud-config
  to perform the configuration.

Guest OS Support
----------------

``make_provisioner`` is intended to run on any system with a POSIX ``/bin/sh``,
including all popular Linux and BSD distros.  Please open an issue on github
if it does not.

License
-------

MIT.


.. _fedora-pack: https://github.com/sapphirecat/fedora-pack
.. _Python: https://www.python.org/
.. _provisioner.ini: https://github.com/sapphirecat/cloud-maker/blob/master/provisioner.ini
