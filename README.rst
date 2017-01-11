distutils-build-without-typehints
=================================

This package provides a setup.py build command that strips typehints from the code during the build.
This is necessary for code bases that use the typehint features of python 3.6 which sometimes do not work in python 3.5 and
are not available before 3.5.

**This package is a quick hack to get packages that do not work with older python version because of type hints to work again. However, it only strips things from the typing module in a very primitive manner.**

Usage
-----

Add the package to your setup requirements::

    setup(
        ...
        setup_requires=[
            ...
            'distutils_build_without_typehints',
            ...
        ],
        ...
    )

And put an alias in the setup.cfg::

    [aliases]
    build=build_without_typehints
