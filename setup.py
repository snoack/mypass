import os
import json
from collections import OrderedDict
from distutils import log

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

try:
    from build_manpages import build_manpages
except ImportError:
    build_manpages = None


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


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as file:
    long_description = file.read()

cmdclass = {
    'build_py': BuildPy,
    'sdist': require_manpages_factory(sdist),
    'bdist_wheel': require_manpages_factory(bdist_wheel),
}
if build_manpages:
    cmdclass['build_manpages'] = build_manpages

setup(name='mypass',
      description='A secure password manager with command line interface',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Sebastian Noack',
      author_email='sebstian.noack@gmail.com',
      url='https://github.com/snoack/mypass',
      license='GPL-3.0-or-later',
      version='2.1',
      packages=['mypass'],
      scripts=['bin/mypass'],
      data_files=[('share/man/man1', [MANPAGE])],
      package_data={'mypass': ['extension/*', 'native-messaging-hosts/*/*.json']},
      install_requires=['pycryptodome', 'argcomplete'],
      python_requires='>=3.4',
      cmdclass=cmdclass,
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
