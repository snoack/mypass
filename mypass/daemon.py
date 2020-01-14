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
import pickle
import socket
import select
import signal

from mypass import Error, SOCKET
from mypass.config import get_config
from mypass.db import Database, makedir_wrapper


class Daemon:
    def __init__(self, sock, db, timeout):
        self._socket = sock
        self._timeout = timeout
        self._shutdown = False

        self._handle_get_credentials = db.get_credentials
        self._handle_get_contexts = db.get_contexts
        self._handle_store_credentials = db.store_credentials
        self._handle_delete_credentials = db.delete_credentials
        self._handle_delete_context = db.delete_context
        self._handle_rename_credentials = db.rename_credentials
        self._handle_rename_context = db.rename_context
        self._handle_change_passphrase = db.change_passphrase
        self._handle_add_context_alias = db.add_context_alias

    def _handle_shutdown(self):
        self._shutdown = True

    def _serve_request(self, file):
        cmd, args = pickle.load(file)

        try:
            response = getattr(self, '_handle_' + cmd.replace('-', '_'))(*args)
        except Error as e:
            response = e

        pickle.dump(response, file)

    def run(self):
        poll = select.poll()
        poll.register(self._socket, select.POLLIN)
        connections = {}

        try:
            while True:
                events = poll.poll(-1 if connections else self._timeout)

                for fd, _ in events:
                    if fd == self._socket.fileno():
                        conn = self._socket.accept()[0]
                        conn_fd = conn.fileno()
                        poll.register(conn_fd, select.POLLIN)
                        connections[conn_fd] = conn.makefile('rwb', 0)
                        conn.close()
                    else:
                        file = connections[fd]
                        try:
                            self._serve_request(file)
                        except EOFError:
                            poll.unregister(fd)
                            del connections[fd]
                            file.close()

                if not events or self._shutdown:
                    break
        finally:
            for file in connections.values():
                file.close()


if __name__ == '__main__':
    try:
        os.umask(0o077)

        with Database(get_config('database', 'path'),
                      sys.stdin.buffer.read().decode('utf-8')) as db, \
             socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            try:
                os.unlink(SOCKET)
            except FileNotFoundError:
                pass

            sock.bind(SOCKET)
            sock.listen(5)

            daemon = Daemon(sock, db, get_config('daemon', 'timeout') * 60000)

            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            devnull_fd = os.open(os.devnull, os.O_RDWR)
            os.dup2(devnull_fd, sys.stdin.fileno())
            os.dup2(devnull_fd, sys.stdout.fileno())
            os.close(devnull_fd)

            log_fd = makedir_wrapper(lambda fn: os.open(fn, os.O_WRONLY |
                                                            os.O_TRUNC |
                                                            os.O_CREAT, 0o666),
                                     get_config('daemon', 'logfile'))
            os.dup2(log_fd, sys.stderr.fileno())
            os.close(log_fd)

            daemon.run()
    except Error as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
