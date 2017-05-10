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

import sys
import os
import struct
import json
import re
import urllib.parse

from mypass import CredentialsDoNotExist, WrongPassphraseOrBrokenDatabase
from mypass.client import Client


def parse_request(length_bytes):
    length = struct.unpack('I', length_bytes)[0]
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode('utf-8'))


def send_response(message):
    data = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('I', len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def get_possible_contexts(url):
    parsed = urllib.parse.urlparse(url)
    parts = parsed.path.split('/')

    while parts:
        yield parsed.netloc + '/'.join(parts)

        tail = parts.pop()
        if tail != '':
            parts.append('')

    if re.search(r'[^0-9.:]', parsed.netloc):
        parts = parsed.netloc.split('.')

        while len(parts) > 2:
            del parts[0]
            yield '.'.join(parts)


class NativeMessagingHost:

    def __init__(self):
        os.umask(0o077)

        while True:
            length_bytes = sys.stdin.buffer.read(4)
            if not length_bytes:
                break

            send_response(self._process_request(parse_request(length_bytes)))

    def _handle_unlock_database(self, client, request):
        if client.status == Client.DATABASE_LOCKED:
            try:
                client.unlock_database(request['passphrase'])
            except WrongPassphraseOrBrokenDatabase:
                return {'status': 'failure'}

        return {'status': 'ok'}

    def _handle_lock_database(self, client, request):
        if client.status == Client.DATABASE_UNLOCKED:
            client.call('shutdown')

        return {'status': 'ok'}

    def _handle_get_credentials(self, client, request):
        if client.status == Client.DATABASE_LOCKED:
            return {'status': 'database-locked'}

        for context in get_possible_contexts(request['url']):
            try:
                credentials = client.call('get-credentials', context)
            except CredentialsDoNotExist:
                continue

            return {'status': 'ok', 'credentials': [dict(zip(['username', 'password'], token)) for token in credentials]}

        return {'status': 'no-credentials'}

    def _process_request(self, request):
        with Client() as client:
            if client.status == Client.DATABASE_DOES_NOT_EXIST:
                return {'status': 'database-does-not-exist'}

            return getattr(self, '_handle_' + request['action'].replace('-', '_'))(client, request)
