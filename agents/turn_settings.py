# SPDX-License-Identifier: MIT
"""The listener tree's own Claude Code settings, checked before every turn.

A chat turn runs `claude -p` in the listener's working directory, and Claude
Code loads that directory's `.claude/settings.json` and `settings.local.json`.
Such a file can carry `env` (a `PATH` with another `timeout`, a
`CLAUDE_CODE_SHELL_PREFIX` that wraps every hook, `LD_PRELOAD`, `BASH_ENV`),
`hooks`, `apiKeyHelper`, MCP servers or a permission mode: each can switch off
or route around the mail guard (change odin-mails-mark, security review of
#256). A `git pull` brings such a file without anyone editing it.

So the rule is an allow-list, after jarvis' `checkout_settings`: a settings
file is safe only when every top-level key is one that cannot run anything or
widen anything (`SAFE_KEYS`), and `permissions` only with `deny`, `ask` and
`allow`. A file that is there and is not a regular JSON object is unsafe (a
symlink, a FIFO, unreadable, too large, not JSON). A missing file is safe.
The listener refuses the turn and reports it in #escalatie.

Not `--setting-sources user`: that would also stop Claude Code from loading
the listener's `.claude/skills`, where the agents' skills are installed.
"""
import json
import os
import stat

SETTINGS_FILES = ("settings.json", "settings.local.json")
SAFE_KEYS = frozenset({"$schema", "model", "includeCoAuthoredBy", "cleanupPeriodDays",
                       "outputStyle", "permissions"})
SAFE_PERMISSION_KEYS = frozenset({"deny", "ask", "allow"})
MAX_BYTES = 64 * 1024


def _read(path):
    """A regular file's bytes, never following a symlink, never blocking."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("not a regular file")
        data = os.read(fd, MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(data) > MAX_BYTES:
        raise OSError("too large")
    return data


def file_problem(path):
    """Why this settings file is unsafe, or None when it is safe or absent."""
    name = os.path.basename(path)
    if not os.path.lexists(path):
        return None
    if os.path.islink(path):
        return f"{name} is a symlink"
    try:
        data = json.loads(_read(path).decode("utf-8"))
    except (OSError, ValueError) as e:
        return f"{name} cannot be read ({e})"
    if not isinstance(data, dict):
        return f"{name} is not a settings object"
    for key in sorted(data):
        if key not in SAFE_KEYS:
            return f"{name} sets {key}"
    perms = data.get("permissions")
    if perms is not None:
        if not isinstance(perms, dict):
            return f"{name} sets permissions"
        for key in sorted(perms):
            if key not in SAFE_PERMISSION_KEYS:
                return f"{name} sets permissions.{key}"
    return None


def problem(directory, user_dir=None):
    """The first problem in `<directory>/.claude/settings*.json`, or None.
    `user_dir` is the user's own `~/.claude`: when the directory is the home
    directory, those are the user's settings, not a project's."""
    claude_dir = os.path.join(os.path.realpath(directory), ".claude")
    user_dir = user_dir if user_dir is not None else os.path.expanduser("~/.claude")
    if os.path.realpath(claude_dir) == os.path.realpath(user_dir):
        return None
    if os.path.islink(claude_dir):
        return ".claude is a symlink"
    for name in SETTINGS_FILES:
        found = file_problem(os.path.join(claude_dir, name))
        if found:
            return f"{claude_dir}/{found}"
    return None
