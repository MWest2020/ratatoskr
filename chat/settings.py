# SPDX-License-Identifier: MIT
"""Settings from the environment, read under one name.

The app is called Ratatoskr, so the settings are called `RATATOSKR_*`. The old
`BOOMHUIS_*` names keep working, and that is not politeness: after a rename a new
image runs against a `.env` that still has the old names. Without a fallback such
an installation dies on an empty database URL or an invitation link that points
nowhere — exactly at the moment you want to be able to go back.

Everything reads through this function, so a next rename cannot leave a read site
behind.

**When this fallback may go.** As soon as no live `.env` uses the `BOOMHUIS_`
prefix any more — check with `grep -l BOOMHUIS_` over the `.env` on the relay VM
and on agent-lxc. Removing it is then a change of its own, not something to
smuggle in here.

That criterion exists because a fallback without an end is not a transition but a
second permanent name. A year from now nobody dares remove it, because nobody
knows whether anything still leans on it — and then the rename was never
finished, it was only postponed.
"""
import os

NEW = "RATATOSKR_"
OLD = "BOOMHUIS_"


def read(name, default=""):
    """`read("URL")` → RATATOSKR_URL, else BOOMHUIS_URL, else `default`.

    An empty string counts as absent: a setting that is accidentally empty in
    `.env` must not block the fallback."""
    for prefix in (NEW, OLD):
        value = os.environ.get(prefix + name, "")
        if value != "":
            return value
    return default


def set_value(name, value):
    """Only for tests and `adminctl`, which put a path from an env file into the
    environment before the storage layer is loaded. Sets the NEW name."""
    os.environ[NEW + name] = value


def is_set(name):
    """Is this setting set anywhere (old or new)?"""
    return read(name) != ""
