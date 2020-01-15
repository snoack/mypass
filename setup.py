import os
import json
from collections import OrderedDict
from distutils import log

from setuptools import setup
from setuptools.command.install import install


class Install(install):
    def _write_manifest(self, vendor):
        manifest = OrderedDict()
        manifest['name'] = 'org.snoack.mypass'
        manifest['description'] = self.distribution.metadata.description
        manifest['path'] = os.path.join(self.config_vars['exec_prefix'], 'bin', 'mypass')
        manifest['type'] = 'stdio'

        if vendor == 'mozilla':
            manifest['allowed_extensions'] = ['mypass@snoack.addons.mozilla.org']
        else:
            manifest['allowed_origins'] = ['chrome-extension://ddbeciaedkkgeiaellofogahfcolmkka/']

        dirname = os.path.join(self.install_lib, 'mypass', 'native-messaging-hosts', vendor)
        self.mkpath(dirname)

        outfile = os.path.join(dirname, manifest['name'] + '.json')
        log.info('Writing %s', outfile)

        if not self.dry_run:
            with open(outfile, 'w') as file:
                json.dump(manifest, file, indent='  ')

    def run(self):
        super().run()

        self._write_manifest('chrome')
        self._write_manifest('mozilla')

        self.copy_tree('extension', os.path.join(self.install_lib, 'mypass', 'extension'))


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as file:
    long_description = file.read()

setup(name='mypass',
      description='A secure password manager with command line interface',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Sebastian Noack',
      author_email='sebstian.noack@gmail.com',
      url='https://github.com/snoack/mypass',
      version='2.0',
      packages=['mypass'],
      scripts=['bin/mypass'],
      install_requires=['pycrypto', 'argcomplete'],
      py_requires='>=3.4',
      cmdclass={'install': Install},
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Information Technology',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Security',
          'Topic :: Utilities',
      ])
