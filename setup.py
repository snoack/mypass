import sys

if sys.version_info[0] < 3:
    sys.stderr.write('Only Python 3 supported\n')
    sys.exit(1)

import os
import json
from collections import OrderedDict
from distutils import log

from setuptools import setup
from setuptools.command.install import install

NATIVE_MESSAGING_MANIFEST_DIRS = {
    'linux': [
        ('chrome', '/etc/opt/chrome/native-messaging-hosts'),
        ('chrome', '/etc/chromium/native-messaging-hosts'),
        ('gecko', '/usr/lib/mozilla/native-messaging-hosts')
    ],
    'darwin': [
        ('chrome', '/Library/Google/Chrome/NativeMessagingHosts'),
        ('chrome', '/Library/Application Support/Chromium/NativeMessagingHosts'),
        ('gecko', '/Library/Application Support/Mozilla/NativeMessagingHosts'),
    ],
}


class install_with_browser(install):
    user_options = install.user_options + [
        ('without-chrome', None, "Don't install native messaging manifest for Chrome extension"),
        ('without-gecko', None, "Don't install native messaging manifest for Firefox extension"),
    ]

    def _create_manifest(self, type):
        manifest = OrderedDict()
        manifest['name'] = 'org.snoack.mypass'
        manifest['description'] = self.distribution.metadata.description
        manifest['path'] = self.distribution.get_command_obj('install_scripts').get_outputs()[0]
        manifest['type'] = 'stdio'

        if type == 'gecko':
            if self.without_gecko:
                return None
            manifest['allowed_extensions'] = ['mypass@snoack.addons.mozilla.org']
        else:
            if self.without_chrome:
                return None
            manifest['allowed_origins'] = ['chrome-extension://ddbeciaedkkgeiaellofogahfcolmkka/']

        return manifest

    def initialize_options(self):
        super().initialize_options()
        self.without_chrome = 0
        self.without_gecko = 0

    def run(self):
        super().run()

        for type, dir in NATIVE_MESSAGING_MANIFEST_DIRS[sys.platform]:
            manifest = self._create_manifest(type)
            if not manifest:
                continue

            dirname = (self.root or '') + dir
            self.mkpath(dirname)

            outfile = os.path.join(dirname, manifest['name'] + '.json')
            log.info("Writing %s", outfile)

            if not self.dry_run:
                with open(outfile, 'w') as file:
                    json.dump(manifest, file, indent='\t')

cmdclass = {}
if sys.platform in NATIVE_MESSAGING_MANIFEST_DIRS:
    cmdclass['install'] = install_with_browser

setup(name='mypass',
      description='A password manager',
      author='Sebastian Noack',
      author_email='sebstian.noack@gmail.com',
      url='https://github.com/snoack/mypass',
      version='1.10',
      packages=['mypass'],
      scripts=['bin/mypass'],
      install_requires=['pycrypto'],
      cmdclass=cmdclass)
