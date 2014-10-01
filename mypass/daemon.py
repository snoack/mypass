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
import pickle
import socket
import select
import errno

from mypass import Error, SOCKET

TIMEOUT = 60 * 30

class Daemon:
	def __init__(self, db):
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

	def _create_socket(self):
		sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			try:
				sock.bind(SOCKET)
			except OSError as e:
				if e.errno != errno.EADDRINUSE:
					raise

				os.unlink(SOCKET)
				sock.bind(SOCKET)

			sock.listen(5)
			return sock
		except:
			self._destroy_socket(sock)
			raise

	def _destroy_socket(self, sock):
		sock.close()

		try:
			os.unlink(SOCKET)
		except FileNotFoundError:
			pass

	def run(self):
		server_socket = self._create_socket()
		try:
			while True:
				sockets = [server_socket] + self._connections
				timeout = None if self._connections else TIMEOUT
				sockets = select.select(sockets, [], [], timeout)[0]

				for sock in sockets:
					if sock is server_socket:
						conn, _ = server_socket.accept()
						self._connections.append(conn)
					else:
						self._serve_request(sock)

				if not sockets or self._shutdown:
					break
		finally:
			for conn in self._connections:
				conn.close()

			self._destroy_socket(server_socket)
