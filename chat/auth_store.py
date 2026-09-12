# SPDX-License-Identifier: EUPL-1.2
"""Storage for people, sessions and invitations — SQLite from the stdlib.

Why SQLite and not JSON like the push registrations: this file is written by
several requests at once (the server is threading), and a JSON file you rewrite
wholesale on every write loses data. SQLite does that atomically and is in the
standard library, so the backend stays dependency-free.

The file lives outside the checkout (`/var/lib/boomhuis`), like `push_subs.json`:
a redeploy must not wipe accounts.

One connection per call. At this volume that is more than fast enough and it
avoids the trouble with `check_same_thread` on a shared connection.

The table and column names are Dutch and stay that way: they are in the database
of every running installation, and renaming them without a migration locks
everyone out. See ADR-0001; that is a change of its own.
"""
import os
import sqlite3
import time

import settings

PATH = settings.read("AUTH_DB", "/var/lib/ratatoskr/auth.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS personen (
  id INTEGER PRIMARY KEY,
  naam TEXT NOT NULL UNIQUE COLLATE NOCASE,
  hash TEXT NOT NULL,
  totp TEXT,
  totp_laatste INTEGER,
  eigenaar INTEGER NOT NULL DEFAULT 0,
  gemaakt INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessies (
  hash TEXT PRIMARY KEY,
  persoon INTEGER NOT NULL,
  csrf TEXT NOT NULL,
  verloopt INTEGER NOT NULL,
  gezien INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS uitnodigingen (
  hash TEXT PRIMARY KEY,
  soort TEXT NOT NULL,          -- 'setup' or 'uitnodiging'
  verloopt INTEGER NOT NULL,
  gebruikt INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pogingen (
  sleutel TEXT PRIMARY KEY,
  aantal INTEGER NOT NULL,
  tot INTEGER NOT NULL
);   -- filled by auth_throttle.py
"""


def _connect():
    directory = os.path.dirname(PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fresh = not os.path.exists(PATH)
    con = sqlite3.connect(PATH, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    if fresh:
        os.chmod(PATH, 0o600)
    return con


def now():
    return int(time.time())


# --- people -----------------------------------------------------------------

def person_count():
    with _connect() as con:
        return con.execute("SELECT COUNT(*) c FROM personen").fetchone()["c"]


def create_person(name, hash_, owner=False):
    """Returns the id, or None when the name already exists."""
    try:
        with _connect() as con:
            cur = con.execute(
                "INSERT INTO personen (naam, hash, eigenaar, gemaakt) VALUES (?,?,?,?)",
                (name, hash_, 1 if owner else 0, now()))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def person_by_name(name):
    with _connect() as con:
        return con.execute("SELECT * FROM personen WHERE naam = ?", (name,)).fetchone()


def person(pid):
    with _connect() as con:
        return con.execute("SELECT * FROM personen WHERE id = ?", (pid,)).fetchone()


def set_hash(pid, hash_):
    with _connect() as con:
        con.execute("UPDATE personen SET hash = ? WHERE id = ?", (hash_, pid))


def set_totp(pid, secret):
    with _connect() as con:
        con.execute("UPDATE personen SET totp = ?, totp_laatste = NULL WHERE id = ?",
                    (secret, pid))


def set_totp_counter(pid, counter):
    with _connect() as con:
        con.execute("UPDATE personen SET totp_laatste = ? WHERE id = ?", (counter, pid))


# --- sessions ---------------------------------------------------------------

def create_session(hash_, pid, csrf, expires):
    with _connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO sessies (hash, persoon, csrf, verloopt, gezien) "
            "VALUES (?,?,?,?,?)", (hash_, pid, csrf, expires, now()))


def session(hash_):
    """The session, or None when it does not exist or has expired."""
    with _connect() as con:
        row = con.execute("SELECT * FROM sessies WHERE hash = ?", (hash_,)).fetchone()
        if row is None:
            return None
        if row["verloopt"] <= now():
            con.execute("DELETE FROM sessies WHERE hash = ?", (hash_,))
            return None
        return row


def extend_session(hash_, expires):
    with _connect() as con:
        con.execute("UPDATE sessies SET verloopt = ?, gezien = ? WHERE hash = ?",
                    (expires, now(), hash_))


def revoke_session(hash_):
    with _connect() as con:
        con.execute("DELETE FROM sessies WHERE hash = ?", (hash_,))


def revoke_all_sessions(pid):
    with _connect() as con:
        con.execute("DELETE FROM sessies WHERE persoon = ?", (pid,))


def purge_sessions():
    with _connect() as con:
        con.execute("DELETE FROM sessies WHERE verloopt <= ?", (now(),))


# --- invitations ------------------------------------------------------------

def create_invite(hash_, kind, expires):
    with _connect() as con:
        con.execute("INSERT OR REPLACE INTO uitnodigingen (hash, soort, verloopt) "
                    "VALUES (?,?,?)", (hash_, kind, expires))


def invite(hash_):
    """Only an unused, unexpired invitation comes back."""
    with _connect() as con:
        return con.execute(
            "SELECT * FROM uitnodigingen WHERE hash = ? AND gebruikt = 0 AND verloopt > ?",
            (hash_, now())).fetchone()


def use_invite(hash_):
    """Mark as used. False when it was already spent — that makes it single-use."""
    with _connect() as con:
        cur = con.execute(
            "UPDATE uitnodigingen SET gebruikt = 1 WHERE hash = ? AND gebruikt = 0 "
            "AND verloopt > ?", (hash_, now()))
        return cur.rowcount == 1


def revoke_invites(kind=None):
    with _connect() as con:
        if kind:
            con.execute("DELETE FROM uitnodigingen WHERE soort = ?", (kind,))
        else:
            con.execute("DELETE FROM uitnodigingen")
