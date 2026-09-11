# SPDX-License-Identifier: EUPL-1.2
"""Instellingen uit de omgeving, onder één naam gelezen.

De app heet Ratatoskr, dus de instellingen heten `RATATOSKR_*`. De oude
`BOOMHUIS_*`-namen blijven werken, en dat is geen beleefdheid: bij een
hernoeming draait er een nieuw image tegen een `.env` die nog de oude namen
heeft. Zonder terugval valt zo'n installatie stil op een lege database-URL of
een uitnodigingslink die nergens heen wijst — precies op het moment dat je
terug wilt kunnen.

Alles leest via deze functie, zodat er bij een volgende hernoeming geen
leesplek kan achterblijven.
"""
import os

NIEUW = "RATATOSKR_"
OUD = "BOOMHUIS_"


def lees(naam, default=""):
    """`lees("URL")` → RATATOSKR_URL, anders BOOMHUIS_URL, anders `default`.

    Een lege string telt als afwezig: een instelling die per ongeluk leeg in
    `.env` staat mag de terugval niet blokkeren."""
    for prefix in (NIEUW, OUD):
        waarde = os.environ.get(prefix + naam, "")
        if waarde != "":
            return waarde
    return default


def zet(naam, waarde):
    """Alleen voor tests en `adminctl`, die een pad uit een env-bestand in de
    omgeving zet voordat de opslaglaag geladen wordt. Zet de NIEUWE naam."""
    os.environ[NIEUW + naam] = waarde


def gezet(naam):
    """Staat deze instelling ergens (oud of nieuw)?"""
    return lees(naam) != ""
