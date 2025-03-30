# Copyright (c) 2014-2025 Sebastian Noack
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
import ctypes.util

from mypass import Error, ConnectionLost, SOCKET
from mypass.config import get_config


def _spawn_daemon():
    lib = ctypes.util.find_library('sqlcipher')
    if not lib:
        raise Error('SQLCipher library is not installed')
    ld_preload = '{} {}'.format(os.environ.get('LD_PRELOAD', ''), lib).lstrip()
    process = subprocess.Popen(
        [sys.executable, '-m', 'mypass.daemon'],
        env=dict(os.environ, LD_PRELOAD=ld_preload),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        bufsize=0
    )
    return (process.stdout, process.stdin)


class Client:
    def __init__(self, shared=True):
        self.shared = shared
        self._pipe = None

        if shared:
            try:
                self._connect()
            except (FileNotFoundError, ConnectionRefusedError):
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _connect(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(SOCKET)
            self._pipe = (sock.makefile('rb', 0),
                          sock.makefile('wb', 0))

    @property
    def database_locked(self):
        return not self._pipe

    def unlock_database(self, passphrase):
        self._pipe = _spawn_daemon()
        self.call('init', passphrase, self.shared)

    def call(self, command, *args):
        reader, writer = self._pipe
        try:
            pickle.dump((command, args), writer)
            output = pickle.load(reader)
        except (BrokenPipeError, EOFError):
            raise ConnectionLost

        if isinstance(output, Error):
            raise output

        return output

    def close(self):
        if self._pipe:
            self._pipe[0].close()
            self._pipe[1].close()


def database_exists():
    try:
        return os.stat(get_config('database', 'path')).st_size > 0
    except FileNotFoundError:
        return False
