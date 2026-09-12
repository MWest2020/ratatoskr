#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Manage accounts from the host, without a browser.

Exists because the web route has a chicken-and-egg problem: you can only log in
once there is an account, and if you cannot reach the app you never get there.
This runs on the machine the installation is on — whoever can get at that can do
everything anyway.

    sudo -E python3 adminctl.py owner mark
    sudo -E python3 adminctl.py invite
    sudo -E python3 adminctl.py people
    sudo -E python3 adminctl.py password mark
    sudo -E python3 adminctl.py delete guest

The password is asked for (twice, not echoed) and is nowhere in your shell
history. `-E` so RATATOSKR_AUTH_DB and RATATOSKR_URL come along from the
environment; without the first it takes the default path.
"""
import getpass
import os
import sys

import settings


def _from_env_file(key):
    """The service reads its settings from chat.env; this script runs beside it
    and would otherwise take the default path and `<your url>` while both are
    lying right next to it. Both namings, new first."""
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


# Before importing auth_store: that reads the path at load time.
if not settings.is_set("AUTH_DB"):
    from_file = _from_env_file("AUTH_DB")
    if from_file:
        settings.set_value("AUTH_DB", from_file)

import auth  # noqa: E402
import auth_store as store  # noqa: E402

MIN_LENGTH = 12


def _ask_password(name):
    # No terminal — `docker compose exec -T`, an install script, an ansible task:
    # then the password comes from stdin. Without this branch `adminctl owner`
    # ends there in an EOFError, and that is exactly the moment a fresh
    # installation has to get its first account.
    # One line, not two: the repeat question is a typo net for humans.
    if not sys.stdin.isatty():
        first = sys.stdin.readline().rstrip("\n")
        if not first:
            sys.exit("no password on stdin (and no terminal to ask on)")
        if len(first) < MIN_LENGTH:
            sys.exit("password must be at least {} characters".format(MIN_LENGTH))
        # If there is a second line, it is a confirmation and it has to match
        # (that is how supplying it through a pipe always worked). One line is
        # fine too: an install script makes no typos.
        second = sys.stdin.readline().rstrip("\n")
        if second and second != first:
            sys.exit("the two passwords differ")
        return first
    first = getpass.getpass("Password for {}: ".format(name))
    if len(first) < MIN_LENGTH:
        sys.exit("password must be at least {} characters".format(MIN_LENGTH))
    if first != getpass.getpass("Once more: "):
        sys.exit("the two passwords differ")
    return first


def _base_url():
    from_env = settings.read("URL") or _from_env_file("URL")
    return from_env.rstrip("/") or "<your boomhuis url>"


def owner(name):
    """The first person. Only as long as there is nobody — after that inviting is
    the way, because making a second owner should not be possible quietly."""
    if store.person_count() > 0:
        sys.exit("there is already an account; use 'invite' or 'password'")
    pid = store.create_person(name, auth.hash_password(_ask_password(name)),
                              owner=True)
    if pid is None:
        sys.exit("that name already exists")
    store.revoke_invites("setup")   # this voids the printed setup link
    print("owner '{}' created. Sign in at: {}/login".format(name, _base_url()))


def invite():
    if store.person_count() == 0:
        sys.exit("there is no owner yet; start with 'owner <name>'")
    token = auth.new_invite("uitnodiging")
    print("{}/login?uitnodiging={}".format(_base_url(), token))
    print("Works once, expires in {} days.".format(auth.INVITE_TTL // 86400))


def people():
    with store._connect() as con:
        rows = con.execute(
            "SELECT naam, eigenaar, totp IS NOT NULL AS tweede FROM personen "
            "ORDER BY gemaakt").fetchall()
    if not rows:
        print("nobody yet")
        return
    for r in rows:
        marks = []
        if r["eigenaar"]:
            marks.append("owner")
        if r["tweede"]:
            marks.append("2FA")
        print("{:<20} {}".format(r["naam"], ", ".join(marks) or "-"))


def password(name):
    p = store.person_by_name(name)
    if p is None:
        sys.exit("unknown name")
    store.set_hash(p["id"], auth.hash_password(_ask_password(name)))
    store.revoke_all_sessions(p["id"])    # whoever had the old one is out
    print("password of '{}' changed; all sessions have been revoked".format(name))


def delete(name):
    p = store.person_by_name(name)
    if p is None:
        sys.exit("unknown name")
    if p["eigenaar"] and store.person_count() > 1:
        sys.exit("this is the owner; make someone else the owner first")
    store.revoke_all_sessions(p["id"])
    with store._connect() as con:
        con.execute("DELETE FROM personen WHERE id = ?", (p["id"],))
    print("'{}' deleted, sessions revoked".format(name))


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
        sys.exit("usage: adminctl.py {} {}".format(
            argv[1], "<name>" if count else "").strip())
    fn(*args)


if __name__ == "__main__":
    main(sys.argv)
