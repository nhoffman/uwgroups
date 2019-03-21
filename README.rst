========================================
Python library and CLI for UW Groups API
========================================

.. contents:: Table of Contents

* API Documentation: https://nhoffman.github.io/uwgroups/

Implements an arbitrary subset of the UW Groups REST API
(https://wiki.cac.washington.edu/display/infra/Groups+Web+Service+REST+API)
that I find useful. Under development.

dependencies
============

* Python 2.7.x
* Tested on Linux and OS X.

installation
============

Set up a virtualenv::

  virtualenv py2-env
  source py2-env/bin/activate
  pip install -U pip

For now, install directly from GitHub::

  pip install git+https://github.com/nhoffman/uwgroups.git

Alternatively, for development, from the top level of the repo (after
installing and activating the virtualenv)::

  pip install -e .
  pip install -r requirements.txt

CLI
===

After installation, the CLI entry point is called ``uwgroups``. For
development, you can invoke the ``uwgroups.py`` from within the cloned
repo::

    % cd uwgroups
    % ./uwgroups.py --help

or::

   % path/to/uwgroups/uwgroups.py --help

When invoked this way, the local version of the package is imported,
even if the version of the package is installed to the system. This is
very handy for development, and can avoid the requirement for a
virtualenv in many cases.

Commands are constructed as follows. Every command starts with the
name of the script, followed by an "action" followed by a series of
required or optional "arguments". The name of the script, the action,
and options and their arguments are entered on the command line
separated by spaces. Help text is available for both the ``uwgroups``
script and individual actions using the ``-h`` or ``--help`` options.

authentication
==============

Authentication to the UW Groups API uses SSL/TLS authentication with
an X.509 certificate in pem format along with the private key used to
generate it. The certificate and key may be concatenated into the same
file, for example::

  -----BEGIN RSA PRIVATE KEY-----
  <key contents>
  -----END RSA PRIVATE KEY-----
  -----BEGIN CERTIFICATE-----
  <cert contents>
  -----END CERTIFICATE-----

In this case, the concatenated key and cert can either be specified on
the command line using ``-c/--cert-file`` before the name of the
subcommand::

  uwgroups -c certfile.pem connect

or using the environment variable ``UWGROUPS_CERT``::

  export UWGROUPS_CERT=certfile.pem
  uwgroups connect

The key may also be provided in a separate fie using ``-k/--key-file``
or ``UWGROUPS_KEY`` as above.

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

Copyright (c) 2017-2019 Noah Hoffman

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
