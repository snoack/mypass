# Copyright (c) 2014 Sebastian Noack
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

import os
import configparser

from mypass import ConfigError

if os.name == 'nt':
	DATA_DIR = os.path.expandvars('%LOCALAPPDATA%')
else:
	DATA_DIR = os.path.expanduser('~/.config')
DATA_DIR = os.path.join(DATA_DIR, 'mypass')

SCHEMA = {
	'daemon': {
		'disabled': False,
		'timeout': 30,
	},
	'database': {
		'path': os.path.join(DATA_DIR, 'db'),
	}
}

config = {}
_error = None

def check_config_errors():
	if _error is not None:
		raise ConfigError(_error)

def _parse():
	global _error

	parser = configparser.ConfigParser()
	try:
		parser.read(os.path.join(DATA_DIR, 'config.ini'))
	except UnicodeDecodeError:
		_error = 'Unexpected encoding in config file'
	except configparser.ParsingError:
		_error = 'Invalid syntax in config file'

	for section, default_options in SCHEMA.items():
		options = config[section] = {}

		for option, value in default_options.items():
			expected_type = type(value)

			try:
				if expected_type is bool:
					value = parser.getboolean(section, option)
				else:
					value = expected_type(parser.get(section, option))
			except ValueError:
				if not _error:
					_error = 'Invalid value for option {!r} in section {!r} in config file'.format(option, section)
			except configparser.Error:
				pass

			options[option] = value

_parse()
