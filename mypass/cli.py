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
import random
import string
import argparse
from getpass import getpass

try:
    import argcomplete
except ImportError:
    argcomplete = None

from mypass import Error, CredentialsDoNotExist, CredentialsAlreadytExist, DaemonFailed
from mypass.client import Client, database_exists
from mypass.config import get_config


def generate_password(length):
    rand = random.SystemRandom()

    chars = [
        rand.choice(string.ascii_lowercase),
        rand.choice(string.ascii_uppercase),
        rand.choice(string.digits),
        rand.choice(string.punctuation),
    ]

    while len(chars) < length:
        chars.append(chr(rand.randint(33, 126)))

    rand.shuffle(chars)
    return ''.join(chars)[:length]


def prompt_new_passphrase():
    passphrase = getpass('New passphrase: ')

    if passphrase != getpass('Verify passphrase: '):
        print("Password doesn't match!", file=sys.stderr)
        sys.exit(1)

    return passphrase


def complete_context(**kwargs):
    with Client() as client:
        if not client.database_locked:
            return client.call('get-contexts')
    return []


def complete_username(parsed_args, **kwargs):
    with Client() as client:
        if not client.database_locked:
            try:
                return [user for user, _ in client.call('get-credentials',
                                                        parsed_args.context)]
            except CredentialsDoNotExist:
                pass
    return []


class CLI:

    def __init__(self):
        try:
            self._parse_arguments()

            with Client() as self._client:
                self._open_database()
                getattr(self, '_call_' + self._args.command)()
        except DaemonFailed:
            sys.exit(1)
        except Error as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print(file=sys.stderr)
            sys.exit(1)

    def _parse_arguments(self):
        self._parser = argparse.ArgumentParser()

        subparsers = self._parser.add_subparsers(dest='command')
        subparsers.required = True

        subparser_get = subparsers.add_parser('get', help='Writes the requested password to stdout')
        subparser_get.add_argument('context').completer = complete_context
        subparser_get.set_defaults(fail_if_db_does_not_exist=True)

        subparser_add = subparsers.add_parser('add', help='Adds the given password to the database')
        subparser_add.add_argument('context').completer = complete_context
        subparser_add.add_argument('username', nargs='?', default='')
        subparser_add.add_argument('password', nargs='?')

        subparser_new = subparsers.add_parser('new', help='Generates a new password and adds it to the database')
        subparser_new.add_argument('context').completer = complete_context
        subparser_new.add_argument('username', nargs='?', default='')
        subparser_new.add_argument('--length', '-l', type=int)

        subparser_remove = subparsers.add_parser('remove', help='Removes a password from the database')
        subparser_remove.add_argument('context').completer = complete_context
        subparser_remove.add_argument('username', nargs='?').completer = complete_username
        subparser_remove.set_defaults(fail_if_db_does_not_exist=True)

        subparser_rename = subparsers.add_parser('rename', help='Changes the context and/or username of saved passwords')
        subparser_rename.add_argument('context').completer = complete_context
        subparser_rename.add_argument('username', nargs='?').completer = complete_username
        subparser_rename.add_argument('--new-context').completer = complete_context
        subparser_rename.add_argument('--new-username')
        subparser_rename.set_defaults(fail_if_db_does_not_exist=True)

        subparser_list = subparsers.add_parser('list', help='Writes the contexts of all passwords to stdout')
        subparser_list.set_defaults(fail_if_db_does_not_exist=True)

        subparser_alias = subparsers.add_parser('alias', help='Creates a new context that refers to the credentials of an existing context')
        subparser_alias.add_argument('context').completer = complete_context
        subparser_alias.add_argument('alias')
        subparser_alias.set_defaults(fail_if_db_does_not_exist=True)

        subparser_changepw = subparsers.add_parser('changepw', help='Changes the master passphrase')
        subparser_changepw.set_defaults(fail_if_db_does_not_exist=True)

        subparser_lock = subparsers.add_parser('lock', help='Closes the database and forgets the master passhrase')
        subparser_lock.set_defaults(exit_if_db_locked=True)

        if argcomplete:
            argcomplete.autocomplete(self._parser, default_completer=None)

        self._args = self._parser.parse_args()

    def _open_database(self):
        if self._client.database_locked:
            if getattr(self._args, 'exit_if_db_locked', False):
                sys.exit(0)

            if database_exists():
                passphrase = getpass('Unlock database: ')
            else:
                if getattr(self._args, 'fail_if_db_does_not_exist', False):
                    print('Database does not exist', file=sys.stderr)
                    sys.exit(1)

                passphrase = prompt_new_passphrase()

            self._client.unlock_database(passphrase)

    def _check_override(self, *args):
        try:
            self._client.call(*args)
        except CredentialsAlreadytExist:
            if input('Credentials already exist. Do you want to '
                     'override them? [y/N] ')[:1].lower() != 'y':
                print('Aborted', file=sys.stderr)
                sys.exit(1)

            self._client.call(*(args + (True,)))

    def _call_get(self):
        credentials = self._client.call('get-credentials', self._args.context)

        if len(credentials) == 1 and credentials[0][0] == '':
            print(credentials[0][1])
            return

        username_width = max(len(token[0]) for token in credentials) + 2
        for username, password in credentials:
            print(username.ljust(username_width), end='')
            print(password)

    def _call_add(self, password=None):
        self._check_override('store-credentials',
                             self._args.context,
                             self._args.username,
                             password or self._args.password or getpass())

    def _call_new(self):
        length = self._args.length

        if length is None:
            length = get_config('password', 'length')

        min_length = 1
        max_length = 10000
        if not (min_length <= length <= max_length):
            self._parser.error('Length of password must be '
                               'between {} and {}, at least 16 '
                               'is recommended'.format(min_length, max_length))

        password = generate_password(length)
        self._call_add(password)
        print(password)

    def _call_remove(self):
        context = self._args.context
        username = self._args.username

        if username is not None:
            self._client.call('delete-credentials', context, username)
        else:
            self._client.call('delete-context', context)

    def _call_rename(self):
        old_context = self._args.context
        new_context = self._args.new_context
        old_username = self._args.username
        new_username = self._args.new_username

        if new_context is None:
            new_context = old_context

        if old_username is not None or new_username is not None:
            self._check_override('rename-credentials',
                                 old_context, old_username or '',
                                 new_context, new_username or '')
        else:
            self._check_override('rename-context', old_context, new_context)

    def _call_list(self):
        for context in self._client.call('get-contexts'):
            print(context)

    def _call_alias(self):
        self._check_override('add-context-alias', self._args.context, self._args.alias)

    def _call_changepw(self):
        self._client.call('change-passphrase', prompt_new_passphrase())

    def _call_lock(self):
        self._client.call('shutdown')
