# Copyright (c) 2017 Sebastian Noack
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

import ctypes
import ctypes.util
import platform
import os
import sys


def _commoncrypto_pbkdf2(data, salt, iterations, buf):
    return 1 - _crypto.CCKeyDerivationPBKDF(2,  # PBKDF2
                                            data, len(data),
                                            salt, len(salt),
                                            3,  # SHA256
                                            iterations,
                                            buf, len(buf))


def _openssl_pbkdf2(data, salt, iterations, buf):
    return _crypto.PKCS5_PBKDF2_HMAC(data, len(data),
                                     salt, len(salt),
                                     iterations,
                                     _crypto.EVP_sha256(),
                                     len(buf), buf)


try:
    if sys.platform == 'darwin':
        _crypto = ctypes.CDLL(os.path.basename(ctypes.util.find_library('System')))
        _crypto.CCKeyDerivationPBKDF.restype = ctypes.c_int
        _crypto.CCKeyDerivationPBKDF.argtypes = [ctypes.c_uint32,
                                                 ctypes.c_char_p,
                                                 ctypes.c_size_t,
                                                 ctypes.c_char_p,
                                                 ctypes.c_size_t,
                                                 ctypes.c_uint32,
                                                 ctypes.c_uint,
                                                 ctypes.c_char_p,
                                                 ctypes.c_size_t]
        _pbkdf2 = _commoncrypto_pbkdf2
    else:
        if sys.platform == 'win32':
            if platform.architecture()[0] == '64bit':
                libname = 'libeay64'
            else:
                libname = 'libeay32'
        else:
            libname = 'crypto'

        libpath = ctypes.util.find_library(libname)
        if not libpath:
            raise OSError('Library {} not found'.format(libpath))

        _crypto = ctypes.CDLL(libpath)
        _crypto.PKCS5_PBKDF2_HMAC.argtypes = [ctypes.c_char_p, ctypes.c_int,
                                              ctypes.c_char_p, ctypes.c_int,
                                              ctypes.c_int, ctypes.c_void_p,
                                              ctypes.c_int, ctypes.c_char_p]
        _crypto.PKCS5_PBKDF2_HMAC.restype = ctypes.c_int
        _crypto.EVP_sha256.restype = ctypes.c_void_p
        _pbkdf2 = _openssl_pbkdf2
except (OSError, AttributeError) as e:
    raise ImportError('Cannot find a compatible cryptographic library. {}'.format(e))


def pbkdf2(data, salt, iterations, keylen):
    buf = ctypes.create_string_buffer(keylen)
    err = _pbkdf2(data, salt, iterations, buf)

    if err == 0:
        raise ValueError('wrong parameters')
    return buf.raw
