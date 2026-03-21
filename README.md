mypass
======

[![Build Status](https://travis-ci.org/snoack/mypass.svg?branch=master)](https://travis-ci.org/snoack/mypass)
[![Pypi Entry](https://badge.fury.io/py/mypass.svg)](https://pypi.python.org/pypi/mypass)

A secure password manager for UNIX (Linux, BSD) that can be used conveniently
from the command line.

I prefer the command line over the GUI, and the lack of password managers that
serve this use case, motivated me to write my own. It also comes with a browser
extension in order to conviniently but securely fill out logins on the web.


Installation
------------

### On Debian/Ubuntu

Debian packages are attached to the [releases on GitHub][1] and can be installed like below:

```
sudo apt install mypass_*.deb
```


### From PyPI

Make sure you have Python 3, `pipx` and SQLCipher installed. If you have not
used `pipx` before, run `pipx ensurepath` once and restart your shell. Then run
the following command for a per-user installation:

```
pipx install mypass
```


#### Command completion (optional)

In order to enable completion of subcommands, contexts and usernames in Bash,
add the following line to your *~/.bashrc*:

```sh
eval "$("$(pipx environment --value PIPX_HOME)/venvs/mypass/bin/register-python-argcomplete" --no-defaults mypass)"
```

For enabling completion in Zsh, Tcsh and Fish please refer to the [`argcomplete` documentation][2].


#### Browser integration (optional)

In order to allow the browser extension to communicate with the host application,
choose `VENDOR` and `MANIFEST_DIR` from the table below, then run:

|               | `VENDOR` | `MANIFEST_DIR`                               |
| ------------- | -------- | -------------------------------------------- |
| Firefox       | mozilla  | ~/.mozilla/native-messaging-hosts            |
| Google Chrome | chrome   | ~/.config/google-chrome/NativeMessagingHosts |
| Chromium      | chrome   | ~/.config/chromium/NativeMessagingHosts      |

```sh
PIPX_VENV="$(pipx environment --value PIPX_HOME)/venvs/mypass"
MYPASS_DIR="$("${PIPX_VENV}/bin/python" -c 'import mypass, os; print(os.path.dirname(mypass.__file__))')"
VENDOR=...
MANIFEST_DIR=...
mkdir -p "$MANIFEST_DIR"
sed 's#"path": ".*"#"path": "'"${PIPX_VENV}"'/bin/mypass"#' "${MYPASS_DIR}/native-messaging-hosts/${VENDOR}/org.snoack.mypass.json" > "${MANIFEST_DIR}/org.snoack.mypass.json"
```

If you want to load the extension in Firefox, please run the following commands,
then restart Firefox:

```sh
mkdir -p ~/.mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}
ln -s "${MYPASS_DIR}/extension" ~/.mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}/mypass@snoack.addons.mozilla.org
```

For Chromium-based browsers, you can install the extension from the [Chrome Web Store][3].


Usage
-----

When you run most of the commands below, you will be prompted for the passhprase
to decrypt/encrypt the credentials with. If the encrypted file doesn't exist yet,
it will be created when you store any credentials for the first time.
By default, a daemon is spawned and shuts down after 30 minutes of inactivity,
so that you don't have to enter your passphrase again when performing multiple
actions within that period.


#### `mypass add <context> [<username>] [<password>]`

Stores credentials for the given *context*.

The *context* can be any unique keyword which you relate to these credentials. But
if the credentials are for a website, it is recommended to use the corresponding
domain as *context*, so that the browser extension finds the credentials, see below.

The *username* is optional, but specifying a username if there is any, allows you
to store multiple username/password pairs for the same context. Also, if a username
is given, it will be used by the browser extension when filling out web forms.

If *password* is omitted you will be prompted for the password. **Passing the
password on the command line is NOT recommeded**, except for import scripts,
as it will end up in your shell's history.


#### `mypass new <context> [<username>]`

Same as `mypass add`, but stores a new random secure password and prints it.


#### `mypass get <context>`

Prints the credentials for the given *context*.


#### `mypass list`

Prints each context (one per line) that any credentials have been stored for.
In order to filter the list, just pipe the output to programs like `grep`.


#### `mypass remove <context> [<username>]`

Deletes credentials from the encrypted storage. If *username* is given, only
this username and the associated password is removed. If *username* is omitted,
the whole *context* is wiped.


#### `mypass rename --new-{context|username}=<newvalue> <context> [<username>]`

Moves credentials around within the encrypted storage.


##### Examples

Renaming a context:

```
mypass rename --new-context=new.example.com old.example.com
```

Changing the username for *example.com* from *john* to *rose*:

```
mypass rename --new-username=rose example.com john
```

Adding a username to a password which has been stored without an associated username:

```
mypass rename --new-username=rose example.com
```


#### `mypass alias <context> <alias>`

Creates a new context that refers to the credentials of an existing context.

Changes to the credentials performed under either context will be reflected
when looking up the credentials for the other context. Removing either context
doesn't remove the credentials as long as the other context exists.


#### `mypass changepw`

Prompts you for a new passphrase. Existing credentials are re-encrypted
using this passphrase.


#### `mypass lock`

Forces the daemon to immediately shutdown, if it is running,
so that you'd have to enter the passphrase again, from now on.


Configuration
-------------

Optionally, you can create a config file under `~/.config/mypass/config.ini`,
in order to override any of the following presets:

```ini
[daemon]
# Minutes of inactivity after which the daemon shuts down, and you have
# to enter the passphrase, the credentials are encrypted with, again.
timeout = 30

# Path to log file any excpetions thrown by the daemon are written to.
logfile = ~/.config/mypass/log

[database]
# Path to the encrypted file storing the credentials.
path = ~/.config/mypass/db

[password]
# Length of newly generated passwords.
length = 16
```


Browser integration
-------------------

If you installed `mypass` on Debian/Ubuntu from the PPA above, next time you
start Chromium or Firefox, the extension should be active. If you installed
`mypass` by other means see above how to install the browser extension.
Note that while the browser extension is optional, it cannot be used standalone
but requires the command line utility to be installed as well.

The extension adds a button to the browser bar that when clicked, fills out login
forms in the active tab, if the document's domain and path (partially) match the
*context* of any stored credentials. If the document's URL is `https://www.example.com/foo/bar`
for example, credentials from following contexts are considered, in this order:

1. `www.example.com/foo/bar`
2. `www.example.com/foo`
3. `www.example.com`
4. `example.com`

The browser extension is intentionally kept simple and doesn't provide functionality
to manage credentials. Please use the command line utility therefore.

[1]: https://github.com/snoack/mypass/releases
[2]: https://argcomplete.readthedocs.io/#zsh-support
[3]: https://chrome.google.com/webstore/detail/mypass/ddbeciaedkkgeiaellofogahfcolmkka
