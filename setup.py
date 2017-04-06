import sys

if sys.version_info[0] < 3:
	sys.stderr.write('Only Python 3 supported\n')
	sys.exit(1)

import os
import json
from collections import OrderedDict

from distutils import log
from distutils.core import setup
from distutils.command.install import install

CHROME_NATIVE_MESSAGING_MANIFEST_DIRS = {
	'linux': (
		'/etc/opt/chrome/native-messaging-hosts',
		'/etc/chromium/native-messaging-hosts',
	),
	'darwin': (
		'/Library/Google/Chrome/NativeMessagingHosts',
		'/Library/Application Support/Chromium/NativeMessagingHosts',
	),
}

class install_with_chrome(install):
	user_options = install.user_options + [
		('without-chrome', None, "Don't install native messaging manifest for Chrome extension"),
	]

	def _create_manifest(self):
		manifest = OrderedDict()
		manifest['name'] = 'org.snoack.mypass'
		manifest['description'] = self.distribution.metadata.description
		manifest['path'] = self.distribution.get_command_obj('install_scripts').get_outputs()[0]
		manifest['type'] = 'stdio'
		manifest['allowed_origins'] = ['chrome-extension://ddbeciaedkkgeiaellofogahfcolmkka/']
		return manifest

	def initialize_options(self):
		super().initialize_options()
		self.without_chrome = 0

	def run(self):
		super().run()

		if not self.without_chrome:
			manifest = self._create_manifest()

			for dir in CHROME_NATIVE_MESSAGING_MANIFEST_DIRS[sys.platform]:
				self.mkpath(dir)

				outfile = os.path.join(dir, manifest['name'] + '.json')
				log.info("Writing %s", outfile)

				if not self.dry_run:
					with open(outfile, 'w') as file:
						json.dump(manifest, file, indent='\t')

cmdclass = {}
if sys.platform in CHROME_NATIVE_MESSAGING_MANIFEST_DIRS:
	cmdclass['install'] = install_with_chrome

setup(
	name='mypass',
	description='A password manager',
	author='Sebastian Noack',
	url='https://github.com/snoack/mypass',
	version='1.0',
	packages=['mypass'],
	scripts=['bin/mypass'],
	cmdclass=cmdclass
)
