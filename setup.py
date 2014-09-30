import sys
from distutils.core import setup

if sys.version_info[0] < 3:
	sys.stderr.write('Only Python 3 supported\n')
	sys.exit(1)

setup(
	name='mypass',
	description='A password manager',
	author='Sebastian Noack',
	url='https://github.com/wallunit/mypass',
	version='1.0',
	packages=['mypass'],
	scripts=['bin/mypass']
)
