import sys

from distutils.core import setup
from distutils.command.install import install

if sys.version_info[0] < 3:
	sys.stderr.write('Only Python 3 supported\n')
	sys.exit(1)

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
		('without-chrome', None, "Don't install native messaging host for Chrome extension"),
	]

	def initialize_options(self):
		super().initialize_options()
		self.without_chrome = 0

	def finalize_options(self):
		super().finalize_options()

		if not self.without_chrome:
			data_files = [
				('/usr/local/lib/mypass', ['chrome/chrome-native-messaging-host'])
			]

			for dir in CHROME_NATIVE_MESSAGING_MANIFEST_DIRS[sys.platform]:
				data_files.append((dir, ['chrome/org.wallunit.mypass.json']))

			self.distribution.data_files = data_files

cmdclass = {}
if sys.platform in CHROME_NATIVE_MESSAGING_MANIFEST_DIRS:
	cmdclass['install'] = install_with_chrome

setup(
	name='mypass',
	description='A password manager',
	author='Sebastian Noack',
	url='https://github.com/wallunit/mypass',
	version='1.0',
	packages=['mypass'],
	scripts=['bin/mypass'],
	cmdclass=cmdclass
)
