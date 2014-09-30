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
import json
import collections
import struct

import Crypto.Cipher.AES
import Crypto.Hash.HMAC
import Crypto.Hash.SHA256
import Crypto.Protocol.KDF

from mypass import WrongPassphraseOrBrokenDatabase, DATABASE

KEY_SIZE = 32
SALT_SIZE = 48
ITERATIONS = 10000

class Database(collections.MutableMapping):
	_header_struct = struct.Struct('{}s{}s'.format(SALT_SIZE, Crypto.Cipher.AES.block_size))

	def __init__(self):
		self._data = {}

	def __getitem__(self, nickname):
		return self._data[nickname.lower()][1]

	def __setitem__(self, nickname, password):
		self._set_item(nickname, password)
		self._write()

	def __delitem__(self, nickname):
		del self._data[nickname.lower()]
		self._write()

	def __iter__(self):
		for _, (nickname, _) in sorted(self._data.items(), key=lambda pair: pair[0]):
			yield nickname

	def __len__(self):
		return len(self._data)

	def _set_item(self, nickname, password):
		self._data[nickname.lower()] = (nickname, password)

	def _init_key(self, passphrase, salt):
		self._key = Crypto.Protocol.KDF.PBKDF2(
			passphrase.encode('utf-8'), salt, KEY_SIZE, ITERATIONS,
			lambda p, s: Crypto.Hash.HMAC.new(p, s, Crypto.Hash.SHA256).digest()
		)
		self._salt = salt

	def _get_cipher(self, iv):
		return Crypto.Cipher.AES.new(self._key, Crypto.Cipher.AES.MODE_CBC, iv)

	def _write(self):
		block_size = Crypto.Cipher.AES.block_size

		plaintext = json.dumps(dict(self), ensure_ascii=False).encode('utf-8')
		plaintext += b' ' * (block_size - len(plaintext) % block_size)

		iv = os.urandom(block_size)
		ciphertext = self._get_cipher(iv).encrypt(plaintext)

		with open(DATABASE, 'wb') as file:
			file.write(self._salt)
			file.write(iv)
			file.write(ciphertext)

	def change_passphrase(self, passphrase):
		self._init_key(passphrase, os.urandom(SALT_SIZE))
		self._write()

	@classmethod
	def decrypt(cls, data, passphrase):
		try:
			salt, iv = cls._header_struct.unpack_from(data)
		except struct.error:
			raise WrongPassphraseOrBrokenDatabase

		db = cls()
		db._init_key(passphrase, salt)

		cipher = db._get_cipher(iv)
		ciphertext = data[cls._header_struct.size:]

		try:
			passwords = json.loads(cipher.decrypt(ciphertext).decode('utf-8'))
		except ValueError:
			raise WrongPassphraseOrBrokenDatabase

		if not isinstance(passwords, dict):
			raise WrongPassphraseOrBrokenDatabase

		for nickname, password in passwords.items():
			db._set_item(nickname, password)

		return db

	@classmethod
	def create(cls, passphrase):
		db = cls()
		db.change_passphrase(passphrase)
		return db
