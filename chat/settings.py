# SPDX-License-Identifier: EUPL-1.2
"""Settings from the environment, read under one name.

The app is called Ratatoskr, so the settings are called `RATATOSKR_*`. The old
`BOOMHUIS_*` names keep working, and that is not politeness: after a rename a new
image runs against a `.env` that still has the old names. Without a fallback such
an installation dies on an empty database URL or an invitation link that points
nowhere — exactly at the moment you want to be able to go back.

Everything reads through this function, so a next rename cannot leave a read site
behind.
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
