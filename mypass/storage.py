# Copyright (c) 2014-2017 Sebastian Noack
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
import struct

import Crypto.Cipher.AES
import Crypto.Hash.HMAC
import Crypto.Hash.SHA256

from mypass import CredentialsDoNotExist, CredentialsAlreadytExist, WrongPassphraseOrBrokenDatabase
from mypass.config import config
from mypass.pbkdf2 import pbkdf2

KEY_SIZE = 32
SALT_SIZE = 48
ITERATIONS = 200000

SINGLE_PASSWORD = ''


class Database:
    _header_struct = struct.Struct('{}s{}s'.format(SALT_SIZE, Crypto.Cipher.AES.block_size))

    def __init__(self):
        self._data = {}

    def _init_key(self, passphrase, salt, iterations=ITERATIONS):
        self._key = pbkdf2(passphrase.encode('utf-8'), salt, iterations, KEY_SIZE)
        self._salt = salt

    def _get_cipher(self, iv):
        return Crypto.Cipher.AES.new(self._key, Crypto.Cipher.AES.MODE_CBC, iv)

    def _decrypt(self, ciphertext, iv, passphrase, salt, iterations=ITERATIONS):
        self._init_key(passphrase, salt, iterations)
        cipher = self._get_cipher(iv)

        try:
            data = json.loads(cipher.decrypt(ciphertext).decode('utf-8'))
        except ValueError:
            raise WrongPassphraseOrBrokenDatabase

        if not isinstance(data, dict):
            raise WrongPassphraseOrBrokenDatabase

        for domain, credentials in data.items():
            self._data[domain.lower()] = (domain, credentials)

    def _write(self):
        block_size = Crypto.Cipher.AES.block_size

        plaintext = json.dumps(dict(self._data.values()), ensure_ascii=False).encode('utf-8')
        plaintext += b' ' * (block_size - len(plaintext) % block_size)

        iv = os.urandom(block_size)
        ciphertext = self._get_cipher(iv).encrypt(plaintext)

        filename = config['database']['path']
        try:
            file = open(filename, 'wb')
        except FileNotFoundError:
            os.makedirs(os.path.dirname(filename))
            file = open(filename, 'wb')

        with file:
            file.write(self._salt)
            file.write(iv)
            file.write(ciphertext)

    def get_credentials(self, domain):
        try:
            credentials = self._data[domain.lower()][1]
        except KeyError:
            raise CredentialsDoNotExist

        return sorted(credentials.items(), key=lambda token: token[0])

    def get_domains(self):
        return [domain for _, (domain, _) in sorted(self._data.items(), key=lambda pair: pair[0])]

    def store_credentials(self, domain, username, password, override=False):
        domain_lower = domain.lower()

        if domain_lower not in self._data:
            credentials = {}
        else:
            credentials = self._data[domain_lower][1]

            if not override and username in credentials:
                raise CredentialsAlreadytExist

            if SINGLE_PASSWORD in credentials:
                if not override:
                    raise CredentialsAlreadytExist

                credentials = {}

        credentials[username] = password
        self._data[domain_lower] = (domain, credentials)
        self._write()

    def store_password(self, domain, password, override=False):
        domain_lower = domain.lower()

        if not override and domain_lower in self._data:
            raise CredentialsAlreadytExist

        self._data[domain_lower] = (domain, {SINGLE_PASSWORD: password})
        self._write()

    def delete_credentials(self, domain, username):
        domain_lower = domain.lower()

        try:
            credentials = self._data[domain_lower][1]
            del credentials[username]
        except KeyError:
            raise CredentialsDoNotExist

        if not credentials:
            del self._data[domain_lower]

        self._write()

    def delete_domain(self, domain):
        try:
            del self._data[domain.lower()]
        except KeyError:
            raise CredentialsDoNotExist

        self._write()

    def rename_credentials(self, old_domain, new_domain, old_username=None, new_username=None, override=False):
        old_domain_lower = old_domain.lower()

        try:
            record = self._data[old_domain_lower]
        except KeyError:
            raise CredentialsDoNotExist
        credentials = record[1]

        try:
            if old_username:
                try:
                    password = credentials.pop(old_username)
                except KeyError:
                    raise CredentialsDoNotExist

                try:
                    if not credentials:
                        del self._data[old_domain_lower]

                    if new_username:
                        self.store_credentials(new_domain, new_username, password, override)
                    else:
                        self.store_password(new_domain, password, override)
                except:
                    credentials[old_username] = password
                    raise
            else:
                del self._data[old_domain_lower]

                if new_username:
                    try:
                        password = credentials[SINGLE_PASSWORD]
                    except KeyError:
                        raise CredentialsDoNotExist

                    self.store_credentials(new_domain, new_username, password, override)
                else:
                    new_domain_lower = new_domain.lower()

                    if not override and new_domain_lower in self._data:
                        raise CredentialsAlreadytExist

                    self._data[new_domain_lower] = (new_domain, credentials)
                    self._write()
        except:
            self._data[old_domain_lower] = record
            raise

    def change_passphrase(self, passphrase):
        self._init_key(passphrase, os.urandom(SALT_SIZE))
        self._write()

    @classmethod
    def decrypt(cls, ciphertext, passphrase):
        try:
            salt, iv = cls._header_struct.unpack_from(ciphertext)
        except struct.error:
            raise WrongPassphraseOrBrokenDatabase

        db = cls()
        ciphertext = ciphertext[cls._header_struct.size:]

        try:
            db._decrypt(ciphertext, iv, passphrase, salt)
        except WrongPassphraseOrBrokenDatabase:
            # Version 1.0 used mere 10k iterations
            # due to a slow PBKDF2 implementation.
            db._decrypt(ciphertext, iv, passphrase, salt, 10000)

            # Re-init the key, so that we use a decent number
            # of iterations if/when changes are written.
            db._init_key(passphrase, salt)

        return db

    @classmethod
    def create(cls, passphrase):
        db = cls()
        db.change_passphrase(passphrase)
        return db
