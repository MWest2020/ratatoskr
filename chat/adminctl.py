#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Accounts beheren vanaf de host, zonder browser.

Bestaat omdat de webweg een kip-en-ei heeft: je kunt pas inloggen als er een
account is, en als je de app niet kunt bereiken kom je er niet. Dit draait op de
machine waar de installatie staat — wie daar bij kan, kan sowieso alles.

    sudo -E python3 adminctl.py owner mark
    sudo -E python3 adminctl.py invite
    sudo -E python3 adminctl.py people
    sudo -E python3 adminctl.py password mark
    sudo -E python3 adminctl.py delete gast

Het wachtwoord wordt gevraagd (twee keer, niet zichtbaar) en staat nergens in
je shell-geschiedenis. `-E` zodat RATATOSKR_AUTH_DB en RATATOSKR_URL uit de
omgeving meekomen; zonder die eerste pakt hij het standaardpad.
"""
import getpass
import os
import sys

import settings


def _from_env_file(key):
    """De service leest zijn instellingen uit chat.env; dit script draait
    ernaast en zou anders het standaardpad en `<jouw url>` pakken terwijl beide
    gewoon naast hem liggen. Beide naamgevingen, nieuw eerst."""
    for name in (settings.NEW + key, settings.OLD + key):
        value = _from_file(name)
        if value:
            return value
    return ""


def _from_file(key):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat.env")
    try:
        with open(path) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                if k == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


# Vóór het importeren van auth_store: die leest het pad bij het laden.
if not settings.is_set("AUTH_DB"):
    from_file = _from_env_file("AUTH_DB")
    if from_file:
        settings.set_value("AUTH_DB", from_file)

import auth  # noqa: E402
import auth_store as store  # noqa: E402

MIN_LENGTH = 12


def _ask_password(name):
    # Geen terminal — `docker compose exec -T`, een installatiescript, een
    # ansible-taak: dan komt het wachtwoord van stdin. Zonder deze tak eindigt
    # `adminctl eigenaar` daar in een EOFError, en dat is precies het moment
    # waarop een verse installatie zijn eerste account moet krijgen.
    # Één regel, niet twee: de herhaalvraag is een typefout-vangnet voor mensen.
    if not sys.stdin.isatty():
        first = sys.stdin.readline().rstrip("\n")
        if not first:
            sys.exit("geen wachtwoord op stdin (en geen terminal om het te vragen)")
        if len(first) < MIN_LENGTH:
            sys.exit("wachtwoord moet minstens {} tekens zijn".format(MIN_LENGTH))
        # Staat er een tweede regel, dan is dat een bevestiging en moet hij
        # kloppen (zo werkte het altijd al bij aanleveren via een pipe). Eén
        # regel is óók goed: een installatiescript maakt geen typefouten.
        second = sys.stdin.readline().rstrip("\n")
        if second and second != first:
            sys.exit("de twee wachtwoorden verschillen")
        return first
    first = getpass.getpass("Wachtwoord voor {}: ".format(name))
    if len(first) < MIN_LENGTH:
        sys.exit("wachtwoord moet minstens {} tekens zijn".format(MIN_LENGTH))
    if first != getpass.getpass("Nog een keer: "):
        sys.exit("de twee wachtwoorden verschillen")
    return first


def _base_url():
    from_env = settings.read("URL") or _from_env_file("URL")
    return from_env.rstrip("/") or "<jouw boomhuis-url>"


def owner(name):
    """De eerste persoon. Alleen zolang er niemand is — daarna is uitnodigen
    de weg, want een tweede eigenaar maken hoort niet stilletjes te kunnen."""
    if store.person_count() > 0:
        sys.exit("er is al een account; gebruik 'invite' of 'password'")
    pid = store.create_person(name, auth.hash_password(_ask_password(name)),
                              owner=True)
    if pid is None:
        sys.exit("die naam bestaat al")
    store.revoke_invites("setup")   # de afgedrukte setup-link vervalt hiermee
    print("eigenaar '{}' aangemaakt. Inloggen: {}/login".format(name, _base_url()))


def invite():
    if store.person_count() == 0:
        sys.exit("er is nog geen eigenaar; begin met 'owner <naam>'")
    token = auth.new_invite("uitnodiging")
    print("{}/login?uitnodiging={}".format(_base_url(), token))
    print("Werkt één keer, verloopt over {} dagen.".format(auth.INVITE_TTL // 86400))


def people():
    with store._connect() as con:
        rows = con.execute(
            "SELECT naam, eigenaar, totp IS NOT NULL AS tweede FROM personen "
            "ORDER BY gemaakt").fetchall()
    if not rows:
        print("nog niemand")
        return
    for r in rows:
        marks = []
        if r["eigenaar"]:
            marks.append("eigenaar")
        if r["tweede"]:
            marks.append("2FA")
        print("{:<20} {}".format(r["naam"], ", ".join(marks) or "-"))


def password(name):
    p = store.person_by_name(name)
    if p is None:
        sys.exit("onbekende naam")
    store.set_hash(p["id"], auth.hash_password(_ask_password(name)))
    store.revoke_all_sessions(p["id"])    # wie het oude had, is eruit
    print("wachtwoord van '{}' gewijzigd; alle sessies zijn ingetrokken".format(name))


def delete(name):
    p = store.person_by_name(name)
    if p is None:
        sys.exit("onbekende naam")
    if p["eigenaar"] and store.person_count() > 1:
        sys.exit("dit is de eigenaar; maak eerst iemand anders eigenaar")
    store.revoke_all_sessions(p["id"])
    with store._connect() as con:
        con.execute("DELETE FROM personen WHERE id = ?", (p["id"],))
    print("'{}' verwijderd, sessies ingetrokken".format(name))


COMMANDS = {
    "owner": (owner, 1),
    "invite": (invite, 0),
    "people": (people, 0),
    "password": (password, 1),
    "delete": (delete, 1),
}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        sys.exit(__doc__)
    fn, count = COMMANDS[argv[1]]
    args = argv[2:]
    if len(args) != count:
        sys.exit("gebruik: adminctl.py {} {}".format(
            argv[1], "<naam>" if count else "").strip())
    fn(*args)


if __name__ == "__main__":
    main(sys.argv)
