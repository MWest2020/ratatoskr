# SPDX-License-Identifier: MIT
"""The brake on login attempts.

A self-hosted installation has no WAF in front of it, so the brake belongs in the
app. A rising wait per key — that is the user name AND the source, each on its
own: you cannot then take one account down by hammering from one address, nor
block one address by guessing names.

Shares the table `pogingen` with auth_store; a separate file because it is a
concern of its own (and because auth_store would otherwise go over the 200 lines
from CLAUDE.md).
"""
from auth_store import _connect, now

def blocked_for(key):
    """Seconds this key still has to wait (0 = go ahead)."""
    with _connect() as con:
        row = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (key,)).fetchone()
        return max(0, row["tot"] - now()) if row else 0


def note_failure(key, wait_from=3, max_wait=300):
    """Count the failure and set the wait. Rising, with a ceiling."""
    with _connect() as con:
        row = con.execute("SELECT * FROM pogingen WHERE sleutel = ?", (key,)).fetchone()
        count = (row["aantal"] if row else 0) + 1
        wait = 0 if count < wait_from else min(2 ** (count - wait_from), max_wait)
        con.execute("INSERT OR REPLACE INTO pogingen (sleutel, aantal, tot) VALUES (?,?,?)",
                    (key, count, now() + wait))


def clear_attempts(key):
    with _connect() as con:
        con.execute("DELETE FROM pogingen WHERE sleutel = ?", (key,))
