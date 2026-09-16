#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Welke van onze timers faalde bij zijn laatste run?

`check_units.py` vergelijkt wat er geïnstalleerd is met wat er in git staat. Dat
zegt niets over of het wérkt. Een systemd-timer die faalt, faalt stil: de timer
blijft `active (waiting)` en plant netjes de volgende run, ongeacht hoe de vorige
afliep. Van buiten ziet een dode taak er gezond uit.

Gemeten op 2026-09-16: `claude-secret-refresh.service` faalde **82 keer in
veertien dagen en slaagde nul keer** — host key verification tegen cp-01 — en de
timer stond al die tijd op `active (waiting)`. Niemand merkte het, want de enige
plek waar het stond was het journaal.

    python3 scripts/check_timers.py          # rapport, niet-nul bij een fout

Kijkt naar de services die onze eigen timers aansturen, niet naar alles op de
machine: wat we niet beheren, hoeven we niet te bewaken.
"""
import argparse
import re
import subprocess
import sys

VAN_ONS = re.compile(r"^(ratatoskr|claude|zettelkast|boomhuis)-")


def systemctl(*args):
    p = subprocess.run(["systemctl", "--user", *args],
                       capture_output=True, text=True, timeout=20)
    return p.stdout if p.returncode == 0 else ""


def timers(uitvoer=None):
    """De timer-units die van ons zijn."""
    tekst = systemctl("list-timers", "--all", "--no-legend") if uitvoer is None else uitvoer
    namen = []
    for regel in tekst.splitlines():
        for woord in regel.split():
            if woord.endswith(".timer") and VAN_ONS.match(woord):
                namen.append(woord)
    return sorted(set(namen))


def toestand(unit, toon=None):
    """(resultaat, exit-code) van de service achter deze timer."""
    service = unit[: -len(".timer")] + ".service"
    tekst = systemctl("show", service, "-p", "Result", "-p", "ExecMainStatus",
                      "-p", "ActiveEnterTimestamp") if toon is None else toon
    velden = dict(r.split("=", 1) for r in tekst.splitlines() if "=" in r)
    return service, velden.get("Result", "?"), velden.get("ExecMainStatus", "?")


def fouten(paren):
    """Welke van deze (service, resultaat, code) is stuk?

    Puur, zodat het te testen is zonder systemd. `Result=success` met exit 0 is
    goed; alles daarbuiten is een melding — ook `?`, want niet kunnen vaststellen
    is geen bewijs dat het goed ging.
    """
    return [(s, r, c) for s, r, c in paren if not (r == "success" and c == "0")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warn", action="store_true",
                    help="melden maar niet falen (voor een host zonder onze timers)")
    a = ap.parse_args()
    units = timers()
    if not units:
        print("timers: geen van onze timers geïnstalleerd")
        return 0
    stuk = fouten([toestand(u) for u in units])
    for service, resultaat, code in stuk:
        print(f"  GEFAALD  {service}  (Result={resultaat}, exit={code})")
    if not stuk:
        print(f"timers: {len(units)} groen")
        return 0
    print(f"\ntimers: {len(stuk)} van {len(units)} faalde bij de laatste run.")
    print("Een timer blijft 'active (waiting)' ook als de service elke keer omvalt;")
    print("kijk met: journalctl --user -u <service> -n 30")
    return 0 if a.warn else 1


if __name__ == "__main__":
    sys.exit(main())
