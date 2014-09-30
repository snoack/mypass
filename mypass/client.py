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
import sys
import pickle
import socket
import signal
import time

from mypass import CommandError, ConnectionLost, SOCKET, DATABASE

class Client:
	DATABASE_DOES_NOT_EXIST = 1
	DATABASE_LOCKED = 2
	CONNECTED = 3

	def __init__(self):
		self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

		try:
			self._sock.connect(SOCKET)
		except (FileNotFoundError, ConnectionRefusedError):
			try:
				with open(DATABASE, 'rb') as file:
					self._ciphertext = file.read()
			except FileNotFoundError:
				self.status = self.DATABASE_DOES_NOT_EXIST
			else:
				self.status = self.DATABASE_LOCKED
		else:
			self.status = self.CONNECTED

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	def _wait_for_connection(self):
		start = time.time()
		while True:
			try:
				self._sock.connect(SOCKET)
				break
			except (FileNotFoundError, ConnectionRefusedError):
				if time.time() - start > 1:
					raise

	def _spawn_daemon(self, db):
		if not os.fork():
			self.close()

			signal.signal(signal.SIGINT, signal.SIG_IGN)
			signal.signal(signal.SIGHUP, signal.SIG_IGN)

			from mypass.daemon import Daemon
			Daemon(db).run()

			sys.exit(0)

		self._wait_for_connection()
		self.status = self.CONNECTED

	def create_database(self, passphrase):
		from mypass.storage import Database
		self._spawn_daemon(Database.create(passphrase))

	def unlock_database(self, passphrase):
		from mypass.storage import Database
		db = Database.decrypt(self._ciphertext, passphrase)
		del self._ciphertext
		self._spawn_daemon(db)

	def call(self, command, *args):
		with self._sock.makefile('rwb', 0) as file:
			try:
				pickle.dump((command, args), file)
				output = pickle.load(file)
			except (BrokenPipeError, EOFError):
				raise ConnectionLost

		if isinstance(output, CommandError):
			raise output

		return output

	def close(self):
		self._sock.close()
