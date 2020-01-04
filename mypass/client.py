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

import sys
import os
import socket
import pickle
import subprocess

from mypass import Error, DaemonFailed, ConnectionLost, SOCKET
from mypass.config import get_config


def _spawn_daemon(passphrase):
    process = subprocess.Popen(
        [sys.executable, '-m', 'mypass.daemon'],
        env=dict(os.environ, LD_PRELOAD=(os.environ.get('LD_PRELOAD', '') +
                                         ' libsqlcipher.so.0').lstrip()),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    with process.stdout:
        with process.stdin:
            process.stdin.write(passphrase.encode('utf-8'))
        process.stdout.read()

    if process.poll() is not None:
        raise DaemonFailed


class Client:

    def __init__(self):
        try:
            self._connect()
        except (FileNotFoundError, ConnectionRefusedError):
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _connect(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(SOCKET)
            self._file = sock.makefile('rwb', 0)

    @property
    def database_locked(self):
        return not self._file

    def unlock_database(self, passphrase):
        _spawn_daemon(passphrase)
        self._connect()

    def call(self, command, *args):
        try:
            pickle.dump((command, args), self._file)
            output = pickle.load(self._file)
        except (BrokenPipeError, EOFError):
            raise ConnectionLost

        if isinstance(output, Error):
            raise output

        return output

    def close(self):
        if self._file:
            self._file.close()


def database_exists():
    try:
        return os.stat(get_config('database', 'path')).st_size > 0
    except FileNotFoundError:
        return False
