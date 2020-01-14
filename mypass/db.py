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

import sqlite3

from mypass import DatabaseError, CredentialsDoNotExist, CredentialsAlreadytExist


def makedir_wrapper(func, filename, exc=FileNotFoundError):
    try:
        return func(filename)
    except exc:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        return func(filename)


def _execute_pragma_with_arg(cursor, pragma, arg):
    cursor.execute("PRAGMA {} = '{}'".format(pragma, arg.replace("'", "''")))


def _connect(filename, passphrase, migrate):
    db = makedir_wrapper(sqlite3.connect, filename, sqlite3.OperationalError)

    try:
        cursor = db.cursor()
        cursor.execute('PRAGMA cipher_version')
        if not cursor.fetchone():
            raise DatabaseError('SQLCipher unavailable')

        _execute_pragma_with_arg(cursor, 'key', passphrase)

        # These are the default settings of SQLCipher 4 except
        # for the key derivation algorithm which is the only one
        # supported by SQLCipher 3. That is the best we can do
        # while preserving compatibility with SQLCipher 3.
        cursor.executescript(
            'PRAGMA cipher_page_size = 4096;'
            'PRAGMA kdf_iter = 256000;'
            'PRAGMA cipher_hmac_algorithm = HMAC_SHA1;'
            'PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1;'
        )

        try:
            cursor.execute('SELECT COUNT(*) FROM sqlite_master')
        except sqlite3.DatabaseError:
            if migrate:
                db.close()
                from mypass.migration import update_from_legacy_db
                if update_from_legacy_db(filename, passphrase):
                    return _connect(filename, passphrase, migrate=False)
            raise DatabaseError('Wrong passphrase or broken database')

        if cursor.fetchone()[0] == 0:
            cursor.executescript(
                '''CREATE TABLE credentials (
                       id INTEGER NOT NULL,
                       username TEXT NOT NULL,
                       password TEXT NOT NULL,
                       PRIMARY KEY (id, username)
                   ) WITHOUT ROWID;
                   CREATE TABLE contexts (
                       id INTEGER NOT NULL,
                       context TEXT COLLATE NOCASE PRIMARY KEY
                   ) WITHOUT ROWID;
                   CREATE INDEX credentials_id_index ON credentials(id);
                   CREATE INDEX contexts_id_index ON contexts(id);'''
            )
    except:
        db.close()
        raise

    return db


def _get_id_or_create_context(cursor, context):
    cursor.execute('SELECT id FROM contexts '
                   'WHERE context = ?', (context,))
    result = cursor.fetchone()
    if result:
        id = result[0]
    else:
        cursor.execute('''SELECT MAX((SELECT IFNULL(MAX(id), 0) FROM credentials),
                                     (SELECT IFNULL(MAX(id), 0) FROM contexts))''')
        id = cursor.fetchone()[0] + 1
        cursor.execute('INSERT INTO contexts (id, context) '
                       'VALUES (?, ?)', (id, context))
    return id


def _get_id(cursor, context, username):
    cursor.execute('''SELECT id
                        FROM credentials
                  INNER JOIN contexts USING (id)
                       WHERE context = ?
                         AND username = ?''', (context, username))
    result = cursor.fetchone()
    if not result:
        raise CredentialsDoNotExist
    return result[0]


def _clear_orphans(cursor, target_table, updated_table, id):
    cursor.execute('SELECT COUNT(*) FROM {} '
                   'WHERE id = ?'.format(updated_table), (id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute('DELETE FROM {} '
                       'WHERE id = ?'.format(target_table), (id,))


def _rename_or_alias_context(sql, db, old_context, new_context, override):
    with db:
        cursor = db.cursor()

        result = None
        if override:
            cursor.execute('SELECT id FROM contexts '
                           'WHERE context = ?', (new_context,))
            result = cursor.fetchone()

        try:
            cursor.execute(sql.format(' OR REPLACE' if override else ''),
                           (new_context, old_context))
        except sqlite3.IntegrityError:
            raise CredentialsAlreadytExist

        if cursor.rowcount == 0:
            raise CredentialsDoNotExist

        if result:
            _clear_orphans(cursor, 'credentials', 'contexts', result[0])


class Database:
    def __init__(self, filename, passphrase):
        self._db = _connect(filename, passphrase, migrate=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_credentials(self, context):
        credentials = list(self._db.execute('''SELECT username, password
                                                 FROM credentials
                                           INNER JOIN contexts USING (id)
                                                WHERE context = ?
                                             ORDER BY username''', (context,)))
        if not credentials:
            raise CredentialsDoNotExist
        return credentials

    def get_contexts(self):
        return [ctx for ctx, in self._db.execute('''SELECT context
                                                      FROM contexts
                                                  ORDER BY context''')]

    def store_credentials(self, context, username, password, override=False):
        with self._db:
            cursor = self._db.cursor()
            id = _get_id_or_create_context(cursor, context)

            try:
                cursor.execute(
                    'INSERT{} INTO credentials (id, username, password) '
                    'VALUES (?, ?, ?)'.format(' OR REPLACE' if override else ''),
                    (id, username, password)
                )
            except sqlite3.IntegrityError:
                raise CredentialsAlreadytExist

    def delete_credentials(self, context, username):
        with self._db:
            cursor = self._db.cursor()
            id = _get_id(cursor, context, username)
            cursor.execute('DELETE FROM credentials '
                           'WHERE id = ? AND username = ?''', (id, username))
            _clear_orphans(cursor, 'contexts', 'credentials', id)

    def delete_context(self, context):
        with self._db:
            cursor = self._db.cursor()
            cursor.execute('SELECT id FROM contexts '
                           'WHERE context = ?', (context,))
            result = cursor.fetchone()
            if not result:
                raise CredentialsDoNotExist
            id = result[0]
            cursor.execute('DELETE FROM contexts '
                           'WHERE context = ?', (context,))
            _clear_orphans(cursor, 'credentials', 'contexts', id)

    def rename_credentials(self, old_context, old_username, new_context, new_username, override=False):
        with self._db:
            cursor = self._db.cursor()
            old_id = _get_id(cursor, old_context, old_username)
            new_id = _get_id_or_create_context(cursor, new_context)

            try:
                cursor.execute(
                    '''UPDATE{} credentials
                            SET id = ?,
                                username = ?
                          WHERE id = ?
                            AND username = ?'''.format(' OR REPLACE' if override else ''),
                    (new_id, new_username, old_id, old_username)
                )
            except sqlite3.IntegrityError:
                raise CredentialsAlreadytExist

            _clear_orphans(cursor, 'contexts', 'credentials', old_id)

    def rename_context(self, old_context, new_context, override=False):
        _rename_or_alias_context('''UPDATE{} contexts
                                         SET context = ?
                                       WHERE context = ?''',
                                 self._db, old_context, new_context, override)

    def add_context_alias(self, context, context_alias, override=True):
        _rename_or_alias_context('''INSERT{} INTO contexts (id, context)
                                           SELECT id, ?
                                             FROM contexts
                                            WHERE context = ?''',
                                 self._db, context, context_alias, override)

    def change_passphrase(self, passphrase):
        _execute_pragma_with_arg(self._db, 'rekey', passphrase)

    def close(self):
        self._db.close()
