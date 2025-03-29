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
import pickle
import socket
import select
import signal

from mypass import Error, SOCKET
from mypass.config import get_config
from mypass.db import Database, makedir_wrapper


def make_db_wrapper(method):
    def wrapper(self, *args):
        return getattr(self._db, method)(*args)
    return wrapper


class Daemon:
    def __init__(self, fd_in, fd_out, timeout):
        self._connections = {fd_in: (os.fdopen(fd_in, 'rb', 0, closefd=False),
                                     os.fdopen(fd_out, 'wb', 0, closefd=False))}
        self._poll = select.poll()
        self._poll.register(fd_in, select.POLLIN)
        self._timeout = timeout
        self._db = None
        self._socket = None
        self._shutdown = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _handle_init(self, passphrase, listen):
        self._db = Database(get_config('database', 'path'), passphrase)

        if listen:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            try:
                os.unlink(SOCKET)
            except FileNotFoundError:
                pass

            self._socket.bind(SOCKET)
            self._socket.listen(5)
            self._poll.register(self._socket, select.POLLIN)

    def _handle_shutdown(self):
        self._shutdown = True

    _handle_get_credentials = make_db_wrapper('get_credentials')
    _handle_get_contexts = make_db_wrapper('get_contexts')
    _handle_store_credentials = make_db_wrapper('store_credentials')
    _handle_delete_credentials = make_db_wrapper('delete_credentials')
    _handle_delete_context = make_db_wrapper('delete_context')
    _handle_rename_credentials = make_db_wrapper('rename_credentials')
    _handle_rename_context = make_db_wrapper('rename_context')
    _handle_change_passphrase = make_db_wrapper('change_passphrase')
    _handle_add_context_alias = make_db_wrapper('add_context_alias')

    def _serve_request(self, reader, writer):
        cmd, args = pickle.load(reader)

        try:
            response = getattr(self, '_handle_' + cmd.replace('-', '_'))(*args)
        except Error as e:
            response = e

        pickle.dump(response, writer)

    def run(self):
        while True:
            events = self._poll.poll(self._timeout)

            for fd, _ in events:
                if self._socket and fd == self._socket.fileno():
                    with self._socket.accept()[0] as conn:
                        self._poll.register(conn, select.POLLIN)
                        self._connections[conn.fileno()] = (
                            conn.makefile('rb', 0),
                            conn.makefile('wb', 0)
                        )
                else:
                    reader, writer = self._connections[fd]
                    try:
                        self._serve_request(reader, writer)
                    except EOFError:
                        self._poll.unregister(fd)
                        del self._connections[fd]
                        reader.close()
                        writer.close()

            if not events or self._shutdown or (not self._socket and not self._connections):
                break

    def close(self):
        for (reader, writer) in self._connections.values():
            reader.close()
            writer.close()
        if self._socket:
            self._socket.close()
        if self._db:
            self._db.close()


if __name__ == '__main__':
    try:
        os.umask(0o077)

        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)

        log_fd = makedir_wrapper(lambda fn: os.open(fn, os.O_WRONLY |
                                                        os.O_TRUNC |
                                                        os.O_CREAT, 0o666),
                                 get_config('daemon', 'logfile'))
        os.dup2(log_fd, sys.stderr.fileno())
        os.close(log_fd)

        with Daemon(sys.stdin.fileno(),
                    sys.stdout.fileno(),
                    get_config('daemon', 'timeout') * 60000) as daemon:
            daemon.run()
    except Error as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
