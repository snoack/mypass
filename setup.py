import os
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from collections import OrderedDict
from distutils import log
from distutils.errors import DistutilsSetupError

from setuptools import Command, setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


MANPAGE = os.path.join('man', 'mypass.1')


def require_manpages_factory(base_command):
    class RequireManpages(base_command):
        def run(self):
            if not os.path.isfile(MANPAGE):
                raise DistutilsSetupError(
                    '{} is missing; run "python3 setup.py build_manpages" first.'.format(MANPAGE)
                )
            super().run()

    return RequireManpages


class BuildPy(build_py):
    def _write_manifest(self, package_dir, vendor):
        manifest = OrderedDict()
        manifest['name'] = 'org.snoack.mypass'
        manifest['description'] = self.distribution.metadata.description
        # pipx/pip users rewrite this template in the README instructions,
        # dh-python installs the console script into /usr/bin.
        manifest['path'] = '/usr/bin/mypass'
        manifest['type'] = 'stdio'

        if vendor == 'mozilla':
            manifest['allowed_extensions'] = ['mypass@snoack.addons.mozilla.org']
        else:
            manifest['allowed_origins'] = ['chrome-extension://ddbeciaedkkgeiaellofogahfcolmkka/']

        dirname = os.path.join(package_dir, 'native-messaging-hosts', vendor)
        self.mkpath(dirname)

        outfile = os.path.join(dirname, manifest['name'] + '.json')
        log.info('Writing %s', outfile)

        with open(outfile, 'w') as file:
            json.dump(manifest, file, indent='  ')

    def run(self):
        super().run()

        package_dir = os.path.join(self.build_lib, 'mypass')
        self._write_manifest(package_dir, 'chrome')
        self._write_manifest(package_dir, 'mozilla')
        self.copy_tree('extension', os.path.join(package_dir, 'extension'))


class BuildManpages(Command):
    description = 'Generate manual pages from README.md and argparse metadata'
    user_options = [
        ('output=', 'O', 'output manpage path'),
        ('readme=', 'R', 'README markdown path'),
    ]

    def initialize_options(self):
        self.output = None
        self.readme = None
        self.argument_parser = None

    def finalize_options(self):
        if self.output is None:
            self.output = MANPAGE
        if self.readme is None:
            self.readme = 'README.md'

    def _extract_section(self, readme, title):
        match = re.search(
            r'^{}\n-+\n(?P<body>.*?)(?=^[^\n]+\n[-=]+\n|\Z)'.format(re.escape(title)),
            readme,
            re.MULTILINE | re.DOTALL,
        )
        if not match:
            raise ValueError('Could not find README section: {}'.format(title))

        return match.group('body').strip()

    def _get_argument_parser(self):
        from mypass.cli import get_argument_parser
        return get_argument_parser()

    def _build_manpage_markdown(self, argument_parser):
        with open(self.readme) as file:
            readme = file.read()

        parts = [
            '# NAME',
            '',
            '{} - {}'.format(argument_parser.prog, self.distribution.get_description()),
            '',
            '# SYNOPSIS',
            '',
            '```text',
            argument_parser.format_usage().strip().split(': ', 1)[-1],
            '```',
        ]

        for title in ['Usage', 'Configuration']:
            parts.extend([
                '',
                '# {}'.format(title.upper()),
                '',
                self._extract_section(readme, title),
            ])

        return '\n'.join(parts).strip() + '\n'

    def run(self):
        argument_parser = self._get_argument_parser()
        build_timestamp = int(os.environ.get('SOURCE_DATE_EPOCH') or time.time())
        build_date = datetime.fromtimestamp(build_timestamp, timezone.utc)
        self.mkpath(os.path.dirname(self.output))
        subprocess.run(
            [
                'pandoc',
                '--standalone',
                '--from=gfm',
                '--to=man',
                '--output', self.output,
                '--metadata=title:{}(1) {} {}'.format(
                    argument_parser.prog.upper(),
                    argument_parser.prog,
                    self.distribution.get_version()
                ),
                '--metadata=author:{} <{}>'.format(
                    self.distribution.get_author(),
                    self.distribution.get_author_email()
                ),
                '--metadata=date:{}'.format(build_date.strftime('%Y-%m-%d'))
            ],
            input=self._build_manpage_markdown(argument_parser),
            text=True,
            check=True
        )


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as file:
    long_description = file.read()

setup(name='mypass',
      description='A secure password manager with command line interface',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Sebastian Noack',
      author_email='sebstian.noack@gmail.com',
      url='https://github.com/snoack/mypass',
      license='GPL-3.0-or-later',
      version='2.2',
      packages=['mypass'],
      scripts=['bin/mypass'],
      data_files=[('share/man/man1', [MANPAGE])],
      package_data={'mypass': ['extension/*', 'native-messaging-hosts/*/*.json']},
      install_requires=['pycryptodome', 'argcomplete'],
      python_requires='>=3.4',
      cmdclass={
          'build_py': BuildPy,
          'build_manpages': BuildManpages,
          'sdist': require_manpages_factory(sdist),
          'bdist_wheel': require_manpages_factory(bdist_wheel),
      },
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Information Technology',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Security',
          'Topic :: Utilities',
      ])
