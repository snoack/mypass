# Copyright (c) 2014-2020 Sebastian Noack
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


class _Path:
    def __init__(self, path):
        self.path = path


DATA_DIR = '~/.config/mypass'

SCHEMA = {
    'daemon': {
        'timeout': 30,
        'logfile': _Path(os.path.join(DATA_DIR, 'log')),
    },
    'database': {
        'path': _Path(os.path.join(DATA_DIR, 'db')),
    },
    'password': {
        'length': 16,
    },
}

_parser = None


def get_config(section, option):
    global _parser

    if not _parser:
        _parser = configparser.ConfigParser()
        try:
            try:
                _parser.read(os.path.join(os.path.expanduser(DATA_DIR), 'config.ini'))
            except UnicodeDecodeError:
                raise ConfigError('Unexpected encoding in config file')
            except configparser.ParsingError:
                raise ConfigError('Invalid syntax in config file')
        except:
            _parser = None
            raise

    default = SCHEMA[section][option]
    is_path = False
    if isinstance(default, _Path):
        default = default.path
        is_path = True

    if isinstance(default, bool):
        func = _parser.getboolean
    else:
        func = getattr(_parser, 'get' + type(default).__name__, _parser.get)

    try:
        value = func(section, option, fallback=default)
    except ValueError:
        raise ConfigError('Invalid value for option {!r} in section '
                          '{!r} in config file'.format(option, section))

    if is_path:
        value = os.path.expanduser(value)

    return value
