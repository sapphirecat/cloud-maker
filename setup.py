# vim: fileencoding=utf-8
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
from cloud_maker import VERSION

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='cloud-maker',

    # TODO: single-source this throughout the project.  see:
    # https://packaging.python.org/en/latest/single_source_version.html
    version=VERSION,

    description='Tools for building cloud images (make_provisioner and fedora2ova)',
    long_description=long_description,
    url='https://github.com/sapphirecat/cloud-maker',

    author='Sapphire Cat',
    author_email='devel@sapphirepaw.org',

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',

        'Environment :: Console',
        'Operating System :: OS Independent',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Installation/Setup',

        # should match "license" above
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='aws cloud ami packer provisioner devops',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'fedora2ova=fedora2ova.app:main',
            'make_provisioner=make_provisioner.app:main',
        ],
    },
)
