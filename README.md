# cloud-maker

Linux Cloud bootstrap scripts (Python version)

A successor to [fedora-pack](https://github.com/sapphirecat/fedora-pack), in a
language that isn’t dead, and that includes batteries.

Generates an image bootstrapping script: given a set of dependencies and a
stage 2 directory, generates a single-file, self-extracting script to install
the dependencies, unpack stage 2, and launch a script from within.

Designed for convenient use as a Packer shell provisioner, or a layer in a
Dockerfile.

# Dependencies

* **Host:** Python 3.x, any OS
* **Guest:** Debian, Ubuntu, Fedora, or Amazon Linux

# License

MIT.
