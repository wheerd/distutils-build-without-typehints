# -*- coding: utf-8 -*-
import os.path

from setuptools import setup

root = os.path.dirname(__file__)

with open(os.path.join(root, 'README.rst')) as f:
    readme = f.read()

setup(
    name='distutils_build_without_typehints',
    use_scm_version=True,
    description='A build command that strips typehints from the code during the build.',
    long_description=readme,
    author='Manuel Krebber',
    author_email='admin@wheerd.de',
    url='https://github.com/wheerd/distutils-build-without-typehints',
    license='MIT',
    zip_safe=True,
    packages=['distutils_build_without_typehints'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    setup_requires=[
        'setuptools_scm >= 1.7.0',
    ],
    entry_points = """\
[distutils.commands]
build_without_typehints = distutils_build_without_typehints.build_without_typehints:build_without_typehints"""
)

