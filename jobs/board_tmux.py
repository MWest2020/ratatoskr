#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""De tmux-sessies op deze host als kaarten.

Waarom dit bestaat. Het bord toonde `!sessie`-werksessies (uit run-bestanden) en
PR's, maar niet de tmux-sessies waarin het meeste werk feitelijk gebeurt. Wie
niet toevallig aangekoppeld zat, zag dus niets — en dan moet Mark vragen wat er
loopt, wat hij op 2026-09-14 ook deed: "kun je dit op het bord tonen zodat ik het
kan volgen, graag per issue ook de tmux sessie naam / project".

Dat is dezelfde vorm als de rest van deze week: de informatie bestáát, alleen
niet op het pad dat gelopen wordt.

Bewust klein gehouden, op Marks eigen antwoord: **naam, project en laatste
activiteit**. Geen issue-nummer — dat valt niet betrouwbaar af te leiden uit een
pane, en verzinnen is erger dan weglaten.

Alleen deze host. Een sessie op de relay-VM is een andere machine met een ander
leven; die erbij halen vraagt een ssh-afhankelijkheid in een producer die nu
niets nodig heeft.
"""
import os
import subprocess

# Eén regel per sessie, met de actieve pane erbij. `session_activity` is de
# laatste activiteit in die sessie (epoch), niet de aanmaaktijd.
FORMAT = ("#{session_name}\t#{session_created}\t#{session_activity}"
          "\t#{session_attached}\t#{pane_current_path}\t#{pane_current_command}")


def tmux_listing(timeout=5):
    """De rauwe regels van `tmux list-sessions`, of [] als er geen tmux draait.

    Geen tmux is geen fout: op een machine zonder sessies hoort het bord gewoon
    geen tmux-kaarten te tonen, niet een leesfout te melden.
    """
    try:
        p = subprocess.run(["tmux", "list-sessions", "-F", FORMAT],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return []
    if p.returncode != 0:
        return []                      # o.a. "no server running on ..."
    return [r for r in p.stdout.splitlines() if r.strip()]


def project(pad, home=None):
    """De projectnaam uit het pad van de actieve pane.

    Twee dingen die de echte data laat zien en die je niet moet doorgeven zoals
    ze binnenkomen:

    - Staat een sessie in de home-map, dan is er geen project. "agent" als
      projectnaam tonen is erger dan niets, want het suggereert iets.
    - Is de werkmap weg, dan hangt tmux er letterlijk " (deleted)" achter. Dat
      is echt nieuws — een sessie in een opgeruimde worktree — maar het hoort
      niet ín de naam.
    """
    pad = (pad or "").rstrip("/")
    weg = pad.endswith(" (deleted)")
    if weg:
        pad = pad[: -len(" (deleted)")].rstrip("/")
    if home and pad == home.rstrip("/"):
        return "—", weg
    return (os.path.basename(pad) or pad or "?"), weg


def parse(regels, now, stil_na=None, home=None):
    """Regels -> kaarten. Puur: geen tmux, geen klok, geen schijf.

    `stil_na` (seconden) laat een sessie weg die al te lang niets deed. Standaard
    uit: een sessie die dagen open staat ís het nieuws, niet de ruis.
    """
    kaarten = []
    for regel in regels:
        deel = regel.split("\t")
        if len(deel) < 6:
            continue                   # onbekende vorm: overslaan, niet raden
        naam, gemaakt, activiteit, aangekoppeld, pad, commando = deel[:6]
        try:
            gemaakt_op, laatst = float(gemaakt), float(activiteit)
        except ValueError:
            continue
        if stil_na is not None and now - laatst > stil_na:
            continue
        naam_project, map_weg = project(pad, home)
        kaarten.append({
            "id": "tmux:" + naam,
            "repo": naam_project,
            "title": naam,
            "column": "building",
            "via": "tmux (aangekoppeld)" if aangekoppeld == "1" else "tmux",
            "age_days": max(0.0, (now - gemaakt_op) / 86400.0),
            "activity": _activiteit(commando, now - laatst, map_weg),
            "who": "mark",
            "url": "",
            "channel": "",
            "source": "tmux",
        })
    return kaarten


def _activiteit(commando, geleden, map_weg=False):
    """Wat de sessie doet, hoe lang geleden dat was, en of de map nog bestaat."""
    delen = [commando or "?", _duur(geleden)]
    if map_weg:
        delen.append("werkmap bestaat niet meer")
    return " · ".join(d for d in delen if d)


def _duur(seconden):
    if seconden < 90:
        return "zojuist"
    if seconden < 5400:
        return f"{int(seconden // 60)} min geleden"
    if seconden < 172800:
        return f"{int(seconden // 3600)} uur geleden"
    return f"{int(seconden // 86400)} dagen geleden"


def tmux_cards(now, stil_na=None, listing=None, home=None):
    """De kaarten voor deze host. `listing` en `home` zijn er voor de tests."""
    return parse(tmux_listing() if listing is None else listing, now, stil_na,
                 home if home is not None else os.path.expanduser("~"))
