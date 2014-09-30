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
from getpass import getuser

DATABASE = os.path.expanduser('~/.config/mypass')
SOCKET = '/tmp/mypass-{}.sock'.format(getuser())

class Error(Exception):
	pass

class CommandError(Error):
	pass

class WrongPassphraseOrBrokenDatabase(Error):
	def __str__(self):
		return 'Wrong passphrase or broken database'

class ConnectionLost(Error):
	def __str__(self):
		return 'Connection lost'

class UnknownNickname(CommandError):
	def __str__(self):
		return 'Unkown nickname'

class NicknameAlreadyExists(CommandError):
	def __str__(self):
		return 'Nickname already exists'
