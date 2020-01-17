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


setup(name='mypass',
      description='A password manager',
      author='Sebastian Noack',
      author_email='sebstian.noack@gmail.com',
      url='https://github.com/snoack/mypass',
      version='1.12',
      packages=['mypass'],
      scripts=['bin/mypass'],
      install_requires=['pycrypto', 'argcomplete'],
      py_requires='>=3.4',
      cmdclass={'install': Install})
