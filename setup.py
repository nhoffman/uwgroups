import glob
import os
import subprocess

from distutils.core import Command
from setuptools import setup, find_packages


class CheckVersion(Command):
    description = 'Confirm that the stored package version is correct'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        with open('uwgroups/data/ver') as f:
            stored_version = f.read().strip()

        git_version = subprocess.check_output(
            ['git', 'describe', '--tags', '--dirty']).strip()

        assert stored_version == git_version
        print 'the current version is', stored_version


subprocess.call(
    ('mkdir -p mkvenv/data && '
     'git describe --tags --dirty > uwgroups/data/ver.tmp '
     '&& mv uwgroups/data/ver.tmp uwgroups/data/ver '
     '|| rm -f uwgroups/data/ver.tmp'),
    shell=True, stderr=open(os.devnull, "w"))

from uwgroups import __version__
package_data = glob.glob('data/*')

params = {'author': 'Your name',
          'author_email': 'Your email',
          'description': 'Package description',
          'name': 'uwgroups',
          'packages': find_packages(),
          'package_dir': {'uwgroups': 'uwgroups'},
          'entry_points': {
              'console_scripts': ['uwgroups = uwgroups.scripts.main:main']
          },
          'version': __version__,
          'package_data': {'uwgroups': package_data},
          'test_suite': 'tests',
          'cmdclass': {'check_version': CheckVersion}
          }

setup(**params)
