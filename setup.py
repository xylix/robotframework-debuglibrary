#!/usr/bin/env python

import io
import os
import re

from setuptools import setup

ROOT = os.path.abspath(os.path.dirname(__file__))


def read(*names, **kwargs):
    with io.open(
        os.path.join(ROOT, *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^VERSION = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

VERSION = find_version('DebugLibrary/version.py')
install_requires = open("requirements.txt").readlines()

setup(
    name='robotframework-repl',
    version=VERSION,
    description='RobotFramework repl',
    long_description=read('README.rst'),
    author='Kerkko Pelttari',
    author_email='kerk.pelt@gmail.com',
    license='New BSD',
    packages=['DebugLibrary'],
    entry_points={
        'console_scripts': [
            'rfrepl= DebugLibrary.shell:shell',
        ],
    },
    zip_safe=False,
    url='https://github.com/xylix/robotframework-repl/',
    keywords='robotframework,debug,shell,repl',
    install_requires=install_requires,
    platforms=['Linux', 'Unix', 'Windows', 'MacOS X'],
    classifiers=[
        'Environment :: Console',
	'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
    ],
)
