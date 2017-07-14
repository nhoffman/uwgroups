======================================
ungapatchka: a python package template
======================================

ungapatchka
    Yiddish word that describes the overly ornate, busy,
    ridiculously over-decorated, and garnished to the point of
    distaste. (www.urbandictionary.com/define.php?term=ungapatchka)

.. contents:: Table of Contents

why?
====

* Provides a basic package framework including a CLI using
  ``argparse`` that divides functionality into subcommands (à la git,
  apt-get, etc)
* The CLI entry point imports the local version of the python package
  when it is invoked using an absolute or relative path (see below).
* Provides some useful utilities, for example ``utils.Opener`` as a
  replacement for ``argparse.FileType``

dependencies
============

* Python 2.7.x
* Tested on Linux and OS X.

installation
============

Clone the project from the git repository to create a new project. You
will need to choose a name for the project (let's say "myproject"),
and for the main script ("runme")::

  git clone https://github.com/nhoffman/ungapatchka.git myproject
  cd myproject && dev/setup.sh myproject runme

Kaopw! A new project with a new git repo::

  % git --no-pager log -n 1
  commit 418307aa88c9733c5e72c1ecff63729d1239c1cc
  Author: Noah Hoffman <noah.hoffman@gmail.com>
  Date:   Tue Sep 30 21:45:43 2014 -0700

      first commit
  % ./runme.py --version
  0.1.0

You'll need to have ``setuptools`` for installation::

  python setup.py install

or use ``pip``::

  pip install .

Subsequent (re)installation with pip should be performed using the
``-U`` option::

  pip install -U .

There's a handy script for bootstrapping a virtualenv (that is, if a
recent version of virtualenv is not available, the source code is
downloaded)::

  dev/venv.py


architecture
============

This project has the following subdirectories:

* ``dev`` - development tools not essential for the primary functionality of the application.
* ``doc`` - files related to project documentation.
* ``ungapatchka`` - the Python package implementing most of the project functionality. This subdirectory is installed to the system.
* ``testfiles`` - files and data used for testing.
* ``tests`` - subpackage implementing unit tests.

Note that ``kapow.py`` and ``ungapatchka`` are placeholder names that
are replaced with your script and project names during setup.

execution
=========

The ``kapow`` script provides the user interface, and uses standard
UNIX command line syntax. Note that for development, it is convenient
to run ``kapow`` from within the project directory by specifying the
relative path to the script::

    % cd ungapatchka
    % ./kapow.py --help

or::

   % path/to/ungapatchka/kapow.py --help

When invoked this way, the local version of the package is imported,
even if the version of the package is installed to the system. This is
very handy for development, and can avoid the requirement for a
virtualenv in many cases.

When the package is installed, an entry point is placed in the 'bin'
directory corresponding to the python environment you used for
installation (so if you installed using ``/usr/local/bin/python``, the
script will be named ``/usr/local/bin/kapow``).

Commands are constructed as follows. Every command starts with the
name of the script, followed by an "action" followed by a series of
required or optional "arguments". The name of the script, the action,
and options and their arguments are entered on the command line
separated by spaces. Help text is available for both the ``kapow``
script and individual actions using the ``-h`` or ``--help`` options.

versions
========

The package version is defined using ``git describe --tags --dirty``
(see http://git-scm.com/docs/git-describe for details).  The version
information is updated and saved in the file ``ungapatchka/data/ver``
when ``setup.py`` is run (on installation, or even by executing
``python setup.py -h``). Run ``python setup.py check_version`` to make
sure that the stored version matches the output of ``git
describe --tags --dirty``.

Add a tag like this::

  git tag -a -m 'version 0.1.0' 0.1.0


unit tests
==========

Unit tests are implemented using the ``unittest`` module in the Python
standard library. The ``tests`` subdirectory is itself a Python
package that implements the tests. All unit tests can be run like this::

    % python setup.py test

A single unit test can be run by referring to a specific module,
class, or method within the ``tests`` package using dot notation::

    % python setup.py test --test-suite tests.test_utils

license
=======

Copyright (c) 2014 Noah Hoffman

Released under the MIT License:

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
