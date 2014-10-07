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

import sys
import os
import pickle
import socket
import select
import signal

from mypass import Error, SOCKET

TIMEOUT = 60 * 30

class Daemon:
	def __init__(self, sock, db):
		self._socket = sock

		self._shutdown = False
		self._connections = []

		self._handle_get_credentials    = db.get_credentials
		self._handle_get_domains        = db.get_domains
		self._handle_store_credentials  = db.store_credentials
		self._handle_store_password     = db.store_password
		self._handle_delete_credentials = db.delete_credentials
		self._handle_delete_domain      = db.delete_domain
		self._handle_change_passphrase  = db.change_passphrase

	def _handle_shutdown(self):
		self._shutdown = True

	def _serve_request(self, conn):
		with conn.makefile('rwb', 0) as file:
			try:
				cmd, args = pickle.load(file)
			except EOFError:
				conn.close()
				self._connections.remove(conn)
				return

			try:
				response = getattr(self, '_handle_' + cmd.replace('-', '_'))(*args)
			except Error as e:
				response = e

			pickle.dump(response, file)

	def run(self):
		try:
			while True:
				sockets = [self._socket] + self._connections
				timeout = None if self._connections else TIMEOUT
				sockets = select.select(sockets, [], [], timeout)[0]

				for sock in sockets:
					if sock is self._socket:
						self._connections.append(sock.accept()[0])
					else:
						self._serve_request(sock)

				if not sockets or self._shutdown:
					break
		finally:
			for conn in self._connections:
				conn.close()

def unlink_socket():
	try:
		os.unlink(SOCKET)
	except FileNotFoundError:
		pass

def spawn_daemon(db):
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
		sock.bind(SOCKET)
		sock.listen(5)

		if not os.fork():
			try:
				signal.signal(signal.SIGINT, signal.SIG_IGN)
				signal.signal(signal.SIGHUP, signal.SIG_IGN)
				signal.signal(signal.SIGTERM, unlink_socket)

				Daemon(sock, db).run()
			finally:
				unlink_socket()

			sys.exit(0)
