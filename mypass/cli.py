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
import sys
import random
import string
import argparse
from getpass import getpass

from mypass import Error, CredentialsAlreadytExist
from mypass.client import Client


def generate_password():
    chars = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(string.punctuation),
    ]

    while len(chars) < 16:
        chars.append(chr(random.randint(33, 126)))

    random.shuffle(chars)
    return ''.join(chars)


def prompt_new_passphrase():
    password = getpass('New passphrase: ')

    if password != getpass('Verify passphrase: '):
        print("Password doesn't match!", file=sys.stderr)
        sys.exit(1)

    return password


class CLI:

    def __init__(self):
        try:
            self._parse_arguments()
            os.umask(0o077)

            with Client() as self._client:
                self._open_database()
                getattr(self, '_call_' + self._args.command)()
        except Error as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print(file=sys.stderr)
            sys.exit(1)

    def _parse_arguments(self):
        parser = argparse.ArgumentParser()

        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        subparser_get = subparsers.add_parser('get', help='Writes the requested password to stdout')
        subparser_get.add_argument('context')
        subparser_get.set_defaults(exit_if_db_does_not_exist=True)

        subparser_add = subparsers.add_parser('add', help='Adds the given password to the database')
        subparser_add.add_argument('context')
        subparser_add.add_argument('username', nargs='?')
        subparser_add.add_argument('password', nargs='?')

        subparser_new = subparsers.add_parser('new', help='Generates a new password and adds it to the database')
        subparser_new.add_argument('context')
        subparser_new.add_argument('username', nargs='?')

        subparser_remove = subparsers.add_parser('remove', help='Removes a password from the database')
        subparser_remove.add_argument('context')
        subparser_remove.add_argument('username', nargs='?')
        subparser_remove.set_defaults(fail_if_db_does_not_exist=True)

        subparser_rename = subparsers.add_parser('rename', help='Changes the context and/or username of saved passwords')
        subparser_rename.add_argument('old_context')
        subparser_rename.add_argument('old_username', nargs='?')
        subparser_rename.add_argument('--new-context')
        subparser_rename.add_argument('--new-username')

        subparser_list = subparsers.add_parser('list', help='Writes the contexts of all passwords to stdout')
        subparser_list.set_defaults(exit_if_db_does_not_exist=True)

        subparser_changepw = subparsers.add_parser('changepw', help='Changes the master passphrase')
        subparser_changepw.set_defaults(fail_if_db_does_not_exist=True)

        subparser_lock = subparsers.add_parser('lock', help='Closes the database and forgets the master passhrase')
        subparser_lock.set_defaults(exit_if_db_locked=True)

        self._args = parser.parse_args()

    def _open_database(self):
        if self._client.status != Client.DATABASE_UNLOCKED and getattr(self._args, 'exit_if_db_locked', False):
            sys.exit(0)

        if self._client.status == Client.DATABASE_DOES_NOT_EXIST:
            if getattr(self._args, 'fail_if_db_does_not_exist', False):
                print('Database does not exist', file=sys.stderr)
                sys.exit(1)

            if getattr(self._args, 'exit_if_db_does_not_exist', False):
                sys.exit(0)

            self._client.create_database(prompt_new_passphrase())

        if self._client.status == Client.DATABASE_LOCKED:
            self._client.unlock_database(getpass('Unlock database: '))

    def _check_override(self, *args):
        try:
            self._client.call(*args)
        except CredentialsAlreadytExist:
            if input('Credentials already exist. Do you want to override them? [y/N] ')[:1].lower() != 'y':
                print('Aborted', file=sys.stderr)
                sys.exit(1)

            self._client.call(*(args + (True,)))

    def _call_get(self):
        credentials = self._client.call('get-credentials', self._args.context)

        if credentials[0][0] == '':
            print(credentials[0][1])
            return

        username_width = max(len(token[0]) for token in credentials) + 2
        for username, password in credentials:
            print(username.ljust(username_width), end='')
            print(password)

    def _call_add(self, password=None):
        context = self._args.context
        username = self._args.username
        password = password or self._args.password or getpass()

        if username:
            self._check_override('store-credentials', context, username, password)
        else:
            self._check_override('store-password', context, password)

    def _call_new(self):
        password = generate_password()
        self._call_add(password)
        print(password)

    def _call_remove(self):
        context = self._args.context
        username = self._args.username

        if username:
            self._client.call('delete-credentials', context, username)
        else:
            self._client.call('delete-context', context)

    def _call_rename(self):
        old_context = self._args.old_context
        new_context = self._args.new_context

        if new_context is None:
            new_context = old_context

        self._check_override('rename-credentials',
                             old_context,
                             new_context,
                             self._args.old_username,
                             self._args.new_username)

    def _call_list(self):
        for context in self._client.call('get-contexts'):
            print(context)

    def _call_changepw(self):
        self._client.call('change-passphrase', prompt_new_passphrase())

    def _call_lock(self):
        self._client.call('shutdown')
