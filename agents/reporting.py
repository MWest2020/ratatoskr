# SPDX-License-Identifier: EUPL-1.2
"""Meldingen per beurt: statistiek naar #statistics, limitaties naar #escalatie.

Apart van listener.py zodat die onder de ≤200-regel-conventie blijft. `send` komt
als callable binnen (de listener bezit de buzz-omgeving en de sleutels); dit
bestand kent alleen het format en het beleid.
"""
import time

import prompts
import providers
import topology

# Hoeveel tussenstanden per beurt, en minimaal hoeveel seconden ertussen.
PROGRESS_MAX = 4
PROGRESS_GAP = 20



def progress_poster(send, cid, cfg, handle):
    """Geeft een callback die tussentijds laat zien WAT de agent doet.

    Waarom: een beurt duurt tot 150s en tot nu toe was dat pure stilte — Mark zag
    niets tot het antwoord er was. Eerste stap gaat er meteen uit, daarna hoogstens
    elke PROGRESS_GAP seconden één regel, met een harde bovengrens. Melden mag de
    beurt nooit vertragen of laten klappen, dus alles in een try.
    """
    state = {"n": 0, "t": 0.0}

    def progress(what):
        now = time.time()
        if state["n"] >= PROGRESS_MAX:
            return
        if state["n"] and now - state["t"] < PROGRESS_GAP:
            return
        state["n"] += 1
        state["t"] = now
        try:
            send(cid, f"⋯ {handle}: {what}", cfg["nsec"], cfg["npub"])
        except Exception:
            pass

    return progress


def report_run(send, channels, handle, cname, cfg, r):
    """Statistiek per beurt naar #statistics, en — alleen als er iets geweigerd is
    of misging — één geaggregeerde melding naar #escalatie (besluit Mark
    2026-09-06: per run, niet per geweigerde aanroep; mens beslist over verruiming).
    Melden mag nooit de beurt zelf laten klappen."""
    try:
        stats = channels.get("statistics")
        if stats:
            requested, actual = r.get("model_requested") or "", r.get("model") or "?"
            # Gevraagd én actual, met een vlag als ze niet matchen: deze regel is
            # het enige waarop Mark kan aflezen of het gedeclareerde model echt
            # afgedwongen wordt. Alleen "wat er draaide" tonen verbergt juist dat.
            model = actual if not requested else (
                f"{requested}→{actual}" + ("" if providers.model_matches(requested, actual)
                                            else "  ⚠ WIJKT AF"))
            line = (f"{handle} · #{cname} · {model} · "
                    f"{r.get('turns', 0)} turns · ${r.get('cost', 0.0):.2f}")
            send(stats, line, cfg["nsec"], cfg["npub"])

        denials, err = r.get("denials") or [], r.get("error") or ""
        # Zelfrapportage uit de tekst: zie prompts.LIMIT_CLAUSE.
        limit = next((ln.split(":", 1)[1].strip()
                      for ln in (r.get("answer") or "").splitlines()
                      if ln.strip().startswith(prompts.LIMIT_MARKER)), "")
        if not denials and not err and not limit:
            return
        esc = channels.get("escalatie")
        if not esc:
            print(f"[listener] {handle}: limitatie maar #escalatie onbekend: "
                  f"{len(denials)} denial(s) {err}", flush=True)
            return
        tools = sorted({d.get("tool_name") or d.get("tool") or "?" for d in denials
                        if isinstance(d, dict)})
        # Advies volgt de OORZAAK. Stond hier eerst altijd "rol verruimen", ook bij
        # een time-out — en dan wijst de melding naar een knop die niets oplost.
        if denials or limit:
            advice = ("beslissen: rol verruimen in de handbook-def "
                      f"({', '.join(tools) if tools else 'de gemelde tool'}), of laten staan.")
        elif err == "timeout":
            advice = (f"beslissen: de vraag was te groot voor één beurt "
                      f"({providers.MAX_TURN_S}s). Opknippen, of als dit vaker gebeurt "
                      f"het zware werk als habitat-run doen — dat heeft 30 minuten.")
        else:
            advice = "beslissen: storing bekijken in het listener-log; geen rolkwestie."
        msg = (f"limitatie · {handle} in #{cname} · model {r.get('model') or '?'}\n"
               + (f"zelf gemeld: {limit}\n" if limit else "")
               + (f"geweigerd: {', '.join(tools)} ({len(denials)}x)\n" if denials else "")
               + (f"storing: {err}\n" if err else "")
               + advice)
        send(esc, msg, cfg["nsec"], cfg["npub"])
    except Exception as e:
        print(f"[listener] melden mislukt ({handle}): {e}", flush=True)


def report_missing_memberships(run, agents, channels, pub2name):
    """Meld bij het opstarten welke agent-lidmaatschappen ontbreken. Geen exit: een
    agent die niet in #statistics zit moet nog steeds antwoorden. Wél luid, want de
    send faalt anders alleen in het log — waargenomen 2026-09-07, toen de
    escalatieketen voor vijf van de acht agents in de praktijk dood was."""
    name2pub = {h: p for p, h in pub2name.items()}
    missing = topology.missing_memberships(
        agents, channels, name2pub, lambda cid: topology.members(run, cid))
    for handle, cname in missing:
        print(f"[listener] LIDMAATSCHAP ONTBREEKT: @{handle} post in #{cname} maar is "
              f"geen lid — die send zal falen (bash ~/bh/members.sh --yes)", flush=True)
    return missing
