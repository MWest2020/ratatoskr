#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Accounts beheren vanaf de host, zonder browser.

Bestaat omdat de webweg een kip-en-ei heeft: je kunt pas inloggen als er een
account is, en als je de app niet kunt bereiken kom je er niet. Dit draait op de
machine waar de installatie staat — wie daar bij kan, kan sowieso alles.

    sudo -E python3 adminctl.py eigenaar mark
    sudo -E python3 adminctl.py uitnodiging
    sudo -E python3 adminctl.py personen
    sudo -E python3 adminctl.py wachtwoord mark
    sudo -E python3 adminctl.py verwijder gast

Het wachtwoord wordt gevraagd (twee keer, niet zichtbaar) en staat nergens in
je shell-geschiedenis. `-E` zodat BOOMHUIS_AUTH_DB en BOOMHUIS_URL uit de
omgeving meekomen; zonder die eerste pakt hij het standaardpad.
"""
import getpass
import os
import sys


def _uit_env_bestand(sleutel):
    """De service leest zijn instellingen uit chat.env; dit script draait
    ernaast en zou anders het standaardpad en `<jouw boomhuis-url>` pakken
    terwijl beide gewoon naast hem liggen."""
    pad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat.env")
    try:
        with open(pad) as f:
            for regel in f:
                k, _, v = regel.strip().partition("=")
                if k == sleutel:
                    return v.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


# Vóór het importeren van auth_store: die leest het pad bij het laden.
if not os.environ.get("BOOMHUIS_AUTH_DB"):
    uit_bestand = _uit_env_bestand("BOOMHUIS_AUTH_DB")
    if uit_bestand:
        os.environ["BOOMHUIS_AUTH_DB"] = uit_bestand

import auth  # noqa: E402
import auth_store as store  # noqa: E402

MIN_LENGTE = 12


def _vraag_wachtwoord(naam):
    # Geen terminal — `docker compose exec -T`, een installatiescript, een
    # ansible-taak: dan komt het wachtwoord van stdin. Zonder deze tak eindigt
    # `adminctl eigenaar` daar in een EOFError, en dat is precies het moment
    # waarop een verse installatie zijn eerste account moet krijgen.
    # Één regel, niet twee: de herhaalvraag is een typefout-vangnet voor mensen.
    if not sys.stdin.isatty():
        eerste = sys.stdin.readline().rstrip("\n")
        if not eerste:
            sys.exit("geen wachtwoord op stdin (en geen terminal om het te vragen)")
        if len(eerste) < MIN_LENGTE:
            sys.exit("wachtwoord moet minstens {} tekens zijn".format(MIN_LENGTE))
        # Staat er een tweede regel, dan is dat een bevestiging en moet hij
        # kloppen (zo werkte het altijd al bij aanleveren via een pipe). Eén
        # regel is óók goed: een installatiescript maakt geen typefouten.
        tweede = sys.stdin.readline().rstrip("\n")
        if tweede and tweede != eerste:
            sys.exit("de twee wachtwoorden verschillen")
        return eerste
    eerste = getpass.getpass("Wachtwoord voor {}: ".format(naam))
    if len(eerste) < MIN_LENGTE:
        sys.exit("wachtwoord moet minstens {} tekens zijn".format(MIN_LENGTE))
    if eerste != getpass.getpass("Nog een keer: "):
        sys.exit("de twee wachtwoorden verschillen")
    return eerste


def _basis():
    uit_omgeving = os.environ.get("BOOMHUIS_URL", "") or _uit_env_bestand("BOOMHUIS_URL")
    return uit_omgeving.rstrip("/") or "<jouw boomhuis-url>"


def eigenaar(naam):
    """De eerste persoon. Alleen zolang er niemand is — daarna is uitnodigen
    de weg, want een tweede eigenaar maken hoort niet stilletjes te kunnen."""
    if store.aantal_personen() > 0:
        sys.exit("er is al een account; gebruik 'uitnodiging' of 'wachtwoord'")
    pid = store.maak_persoon(naam, auth.hash_wachtwoord(_vraag_wachtwoord(naam)),
                             eigenaar=True)
    if pid is None:
        sys.exit("die naam bestaat al")
    store.trek_uitnodigingen_in("setup")   # de afgedrukte setup-link vervalt hiermee
    print("eigenaar '{}' aangemaakt. Inloggen: {}/login".format(naam, _basis()))


def uitnodiging():
    if store.aantal_personen() == 0:
        sys.exit("er is nog geen eigenaar; begin met 'eigenaar <naam>'")
    token = auth.nieuwe_uitnodiging("uitnodiging")
    print("{}/login?uitnodiging={}".format(_basis(), token))
    print("Werkt één keer, verloopt over {} dagen.".format(auth.UITNODIGING_DUUR // 86400))


def personen():
    with store._verbind() as con:
        rijen = con.execute(
            "SELECT naam, eigenaar, totp IS NOT NULL AS tweede FROM personen "
            "ORDER BY gemaakt").fetchall()
    if not rijen:
        print("nog niemand")
        return
    for r in rijen:
        merk = []
        if r["eigenaar"]:
            merk.append("eigenaar")
        if r["tweede"]:
            merk.append("2FA")
        print("{:<20} {}".format(r["naam"], ", ".join(merk) or "-"))


def wachtwoord(naam):
    p = store.persoon_op_naam(naam)
    if p is None:
        sys.exit("onbekende naam")
    store.zet_hash(p["id"], auth.hash_wachtwoord(_vraag_wachtwoord(naam)))
    store.trek_alle_sessies_in(p["id"])    # wie het oude had, is eruit
    print("wachtwoord van '{}' gewijzigd; alle sessies zijn ingetrokken".format(naam))


def verwijder(naam):
    p = store.persoon_op_naam(naam)
    if p is None:
        sys.exit("onbekende naam")
    if p["eigenaar"] and store.aantal_personen() > 1:
        sys.exit("dit is de eigenaar; maak eerst iemand anders eigenaar")
    store.trek_alle_sessies_in(p["id"])
    with store._verbind() as con:
        con.execute("DELETE FROM personen WHERE id = ?", (p["id"],))
    print("'{}' verwijderd, sessies ingetrokken".format(naam))


OPDRACHTEN = {
    "eigenaar": (eigenaar, 1),
    "uitnodiging": (uitnodiging, 0),
    "personen": (personen, 0),
    "wachtwoord": (wachtwoord, 1),
    "verwijder": (verwijder, 1),
}


def main(argv):
    if len(argv) < 2 or argv[1] not in OPDRACHTEN:
        sys.exit(__doc__)
    fn, aantal = OPDRACHTEN[argv[1]]
    args = argv[2:]
    if len(args) != aantal:
        sys.exit("gebruik: adminctl.py {} {}".format(
            argv[1], "<naam>" if aantal else "").strip())
    fn(*args)


if __name__ == "__main__":
    main(sys.argv)
