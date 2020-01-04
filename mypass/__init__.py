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

from getpass import getuser

SOCKET = '/tmp/mypass-{}.sock'.format(getuser())


class Error(Exception):
    pass


class ConfigError(Error):
    pass


class DatabaseError(Error):
    pass


class CredentialsDoNotExist(Error):

    def __str__(self):
        return 'Credentials do not exist'


class CredentialsAlreadytExist(Error):

    def __str__(self):
        return 'Credentials already exist'


class DaemonFailed(Error):

    def __str__(self):
        return 'Failed to spawn daemon'


class ConnectionLost(Error):

    def __str__(self):
        return 'Connection lost'
