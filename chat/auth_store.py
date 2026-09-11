# SPDX-License-Identifier: EUPL-1.2
"""Opslag voor personen, sessies en uitnodigingen — SQLite uit de stdlib.

Waarom SQLite en geen JSON zoals de push-registraties: dit bestand wordt door
meerdere verzoeken tegelijk geschreven (de server is threading), en een JSON die
je bij elke schrijf helemaal herschrijft verliest dan gegevens. SQLite doet dat
atomair en zit in de standaardbibliotheek, dus de backend blijft dependency-loos.

Het bestand staat buiten de checkout (`/var/lib/boomhuis`), net als
`push_subs.json`: een redeploy mag geen accounts wissen.

Per aanroep één verbinding. Dat is bij dit volume ruim snel genoeg en het
voorkomt het gedoe met `check_same_thread` op een gedeelde verbinding.
"""
import os
import sqlite3
import time

import instellingen

PAD = instellingen.lees("AUTH_DB", "/var/lib/ratatoskr/auth.db")

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
  soort TEXT NOT NULL,          -- 'setup' of 'uitnodiging'
  verloopt INTEGER NOT NULL,
  gebruikt INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pogingen (
  sleutel TEXT PRIMARY KEY,
  aantal INTEGER NOT NULL,
  tot INTEGER NOT NULL
);   -- gevuld door auth_rem.py
"""


def _verbind():
    map_ = os.path.dirname(PAD)
    if map_:
        os.makedirs(map_, exist_ok=True)
    nieuw = not os.path.exists(PAD)
    con = sqlite3.connect(PAD, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    if nieuw:
        os.chmod(PAD, 0o600)
    return con


def nu():
    return int(time.time())


# --- personen ---------------------------------------------------------------

def aantal_personen():
    with _verbind() as con:
        return con.execute("SELECT COUNT(*) c FROM personen").fetchone()["c"]


def maak_persoon(naam, hash_, eigenaar=False):
    """Geeft het id, of None wanneer de naam al bestaat."""
    try:
        with _verbind() as con:
            cur = con.execute(
                "INSERT INTO personen (naam, hash, eigenaar, gemaakt) VALUES (?,?,?,?)",
                (naam, hash_, 1 if eigenaar else 0, nu()))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def persoon_op_naam(naam):
    with _verbind() as con:
        return con.execute("SELECT * FROM personen WHERE naam = ?", (naam,)).fetchone()


def persoon(pid):
    with _verbind() as con:
        return con.execute("SELECT * FROM personen WHERE id = ?", (pid,)).fetchone()


def zet_hash(pid, hash_):
    with _verbind() as con:
        con.execute("UPDATE personen SET hash = ? WHERE id = ?", (hash_, pid))


def zet_totp(pid, geheim):
    with _verbind() as con:
        con.execute("UPDATE personen SET totp = ?, totp_laatste = NULL WHERE id = ?",
                    (geheim, pid))


def zet_totp_teller(pid, teller):
    with _verbind() as con:
        con.execute("UPDATE personen SET totp_laatste = ? WHERE id = ?", (teller, pid))


# --- sessies ----------------------------------------------------------------

def maak_sessie(hash_, pid, csrf, verloopt):
    with _verbind() as con:
        con.execute(
            "INSERT OR REPLACE INTO sessies (hash, persoon, csrf, verloopt, gezien) "
            "VALUES (?,?,?,?,?)", (hash_, pid, csrf, verloopt, nu()))


def sessie(hash_):
    """De sessie, of None als hij niet bestaat of verlopen is."""
    with _verbind() as con:
        rij = con.execute("SELECT * FROM sessies WHERE hash = ?", (hash_,)).fetchone()
        if rij is None:
            return None
        if rij["verloopt"] <= nu():
            con.execute("DELETE FROM sessies WHERE hash = ?", (hash_,))
            return None
        return rij


def verleng_sessie(hash_, verloopt):
    with _verbind() as con:
        con.execute("UPDATE sessies SET verloopt = ?, gezien = ? WHERE hash = ?",
                    (verloopt, nu(), hash_))


def trek_sessie_in(hash_):
    with _verbind() as con:
        con.execute("DELETE FROM sessies WHERE hash = ?", (hash_,))


def trek_alle_sessies_in(pid):
    with _verbind() as con:
        con.execute("DELETE FROM sessies WHERE persoon = ?", (pid,))


def ruim_sessies_op():
    with _verbind() as con:
        con.execute("DELETE FROM sessies WHERE verloopt <= ?", (nu(),))


# --- uitnodigingen ----------------------------------------------------------

def maak_uitnodiging(hash_, soort, verloopt):
    with _verbind() as con:
        con.execute("INSERT OR REPLACE INTO uitnodigingen (hash, soort, verloopt) "
                    "VALUES (?,?,?)", (hash_, soort, verloopt))


def uitnodiging(hash_):
    """Alleen een ongebruikte, niet-verlopen uitnodiging komt terug."""
    with _verbind() as con:
        return con.execute(
            "SELECT * FROM uitnodigingen WHERE hash = ? AND gebruikt = 0 AND verloopt > ?",
            (hash_, nu())).fetchone()


def gebruik_uitnodiging(hash_):
    """Markeer als gebruikt. False wanneer hij al op was — dat maakt hem eenmalig."""
    with _verbind() as con:
        cur = con.execute(
            "UPDATE uitnodigingen SET gebruikt = 1 WHERE hash = ? AND gebruikt = 0 "
            "AND verloopt > ?", (hash_, nu()))
        return cur.rowcount == 1


def trek_uitnodigingen_in(soort=None):
    with _verbind() as con:
        if soort:
            con.execute("DELETE FROM uitnodigingen WHERE soort = ?", (soort,))
        else:
            con.execute("DELETE FROM uitnodigingen")
