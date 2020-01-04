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

import os
import json
import tempfile
import hashlib

import Crypto.Cipher.AES
import sqlite3

from mypass import CredentialsAlreadytExist
from mypass.db import Database


def update_from_legacy_db(filename, passphrase):
    with open(filename, 'rb') as file:
        salt = file.read(48)
        iv = file.read(Crypto.Cipher.AES.block_size)
        ciphertext = file.read()

    if not ciphertext or len(ciphertext) % Crypto.Cipher.AES.block_size:
        return False

    for iterations in [200000, 10000]:
        key = hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'),
                                  salt, iterations, 32)
        cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, iv)

        try:
            data = json.loads(cipher.decrypt(ciphertext).decode('utf-8'))
        except ValueError:
            continue

        fd, tempfilename = tempfile.mkstemp('.db', dir=os.path.dirname(filename))
        os.close(fd)

        try:
            with Database(tempfilename, passphrase) as db:
                for context, credentials in data.items():
                    for username, password in credentials.items():
                        db.store_credentials(context, username, password)
        except BaseException as e:
            os.unlink(tempfilename)
            if isinstance(e, (AttributeError,
                              CredentialsAlreadytExist,
                              sqlite3.InterfaceError)):
                continue
            raise

        os.rename(tempfilename, filename)

        return True

    return False
