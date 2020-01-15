import os
import re
import string

import pexpect
import pytest

TIMEOUT = 3


@pytest.fixture(autouse=True)
def setup(tmpdir):
    pexpect.run('mypass lock')
    os.environ['HOME'] = str(tmpdir.mkdir('home'))
    yield
    pexpect.run('mypass lock')


def run(cmd, events=[]):
    child = pexpect.spawn(cmd, timeout=TIMEOUT)

    for expected, response in events:
        child.expect(r'^' + re.escape(expected))
        if response is not None:
            child.sendline(response)
        child.expect(r'^\r\n')

    child.wait()
    assert child.read() == b''
    child.close()
    assert child.status == 0


def test_cli():
    run('mypass add foo.example.com', [('New passphrase: ', 'masterpw'),
                                       ('Verify passphrase: ', 'masterpw'),
                                       ('Password: ', 'password1')])
    run('mypass alias foo.example.com same-as-foo.example.com')
    run('mypass add bar.example.com jane', [('Password: ', 'password2')])
    run('mypass add bar.example.com john password3')

    output, status = pexpect.runu('mypass new bar.example.com jack',
                                  withexitstatus=True, timeout=TIMEOUT)
    assert status == 0
    assert output.endswith('\r\n')
    passwd = output[:-2]
    assert len(passwd) == 16
    chars = set(passwd)
    assert chars.intersection(string.ascii_lowercase)
    assert chars.intersection(string.ascii_uppercase)
    assert chars.intersection(string.digits)
    assert chars.intersection(string.punctuation)
    assert chars.issubset(string.ascii_letters +
                          string.digits +
                          string.punctuation)

    run('mypass lock')
    run('mypass list', [('Unlock database: ', 'masterpw'),
                        ('bar.example.com', None),
                        ('foo.example.com', None),
                        ('same-as-foo.example.com', None)])
    run('mypass get foo.example.com', [('password1', None)])
    run('mypass get bar.example.com', [('jack  ' + passwd, None),
                                       ('jane  password2', None),
                                       ('john  password3', None)])
    run('mypass remove foo.example.com')
    run('mypass remove bar.example.com jack')
    run('mypass list', [('bar.example.com', None),
                        ('same-as-foo.example.com', None)])
    run('mypass get bar.example.com', [('jane  password2', None),
                                       ('john  password3', None)])
    run('mypass get same-as-foo.example.com', [('password1', None)])
    run('mypass rename bar.example.com --new-context=new.example.com')
    run('mypass rename new.example.com jane --new-context=bar.example.com')
    run('mypass rename new.example.com john --new-username=jeff')
    run('mypass list', [('bar.example.com', None),
                        ('new.example.com', None),
                        ('same-as-foo.example.com', None)])
    run('mypass get new.example.com', [('jeff  password3', None)])
    run('mypass get bar.example.com', [('password2', None)])
    run('mypass changepw', [('New passphrase: ', 'masterpw2'),
                            ('Verify passphrase: ', 'masterpw2')])
    run('mypass lock')
    run('mypass list', [('Unlock database: ', 'masterpw2'),
                        ('bar.example.com', None),
                        ('new.example.com', None),
                        ('same-as-foo.example.com', None)])


def test_bash_completion():
    run('mypass add example.com joe pw', [('New passphrase: ', 'masterpw'),
                                          ('Verify passphrase: ', 'masterpw')])

    shell = pexpect.spawn('bash --norc',
                          env=dict(os.environ, PS1='$ '),
                          timeout=TIMEOUT)
    shell.sendline('eval "$(register-python-argcomplete --no-defaults mypass)"')
    shell.readline()

    for input, completed in [('mypass g', 'et'),
                             ('mypass get e', 'xample.com'),
                             ('mypass ad', 'd'),
                             ('mypass add e', 'xample.com'),
                             ('mypass n', 'ew'),
                             ('mypass new e', 'xample.com'),
                             ('mypass rem', 'ove'),
                             ('mypass remove e', 'xample.com'),
                             ('mypass remove example.com j', 'oe'),
                             ('mypass al', 'ias'),
                             ('mypass alias e', 'xample.com'),
                             ('mypass ren', 'ame'),
                             ('mypass rename e', 'xample.com'),
                             ('mypass rename example.com j', 'oe'),
                             ('mypass rename --new-context=e', 'xample.com')]:
        shell.send(input + '\t')
        shell.expect(r'^\$ {} '.format(re.escape(input + completed)))
        shell.sendintr()
        shell.expect(r'^\^C\r\n')
