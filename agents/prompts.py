# SPDX-License-Identifier: EUPL-1.2
"""Context- en prompt-bouwers voor de listener, apart zodat listener.py onder de
≤200-regel-conventie blijft. Puur: alle afhankelijkheden (root-pad, vloot,
naam-map) komen als parameters binnen, geen module-globals van de listener.
"""
import os
import re

_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")  # kanaalnaam → bestandspad: geen ../ of /


def mentioned(content, handle):
    """Wordt @handle genoemd? Woordgrens links én rechts: rechts zodat '@architect'
    niet op '@architectuur' triggert, links zodat 'deploy@bouwer' (of een adres in
    een snippet) niet als mention telt. Handles zijn a-z0-9_-."""
    return re.search(r"(?<![\w-])@" + re.escape(handle) + r"(?![\w-])", content, re.I) is not None


def channel_knowledge(root, cname):
    """Per-kanaal kennis: knowledge/<kanaal>.md wordt als context aan elke
    agent-beurt in dat kanaal meegegeven. Leeg = geen extra context. De kanaalnaam
    komt uit de relay (niet meer alleen channels.yml), dus we valideren 'm streng
    tegen `_SAFE_NAME` vóór 'ie in een pad belandt — anders zou `../..`-naam een
    path-traversal-read geven."""
    if not _SAFE_NAME.match(cname or ""):
        return ""
    try:
        return open(os.path.join(root, "knowledge", f"{cname}.md")).read().strip()[:4000]
    except OSError:
        return ""


def live_text(root):
    """Wat er nu draait (knowledge/_live.md, door orchestrator/live.py gegenereerd)
    — liveness-context voor de hub. Leeg = onbekend."""
    try:
        return open(os.path.join(root, "knowledge", "_live.md")).read().strip()[:4000]
    except OSError:
        return ""


def roster_text(agents, hub=None):
    """Korte samenvatting van de huidige vloot — context voor de hub. `hub` valt
    buiten de lijst: die leest over zichzelf niets nieuws."""
    lines = ["Huidige agent-vloot (uit de handbook-registry):"]
    for h, c in agents.items():
        if h == hub:
            continue
        first = (c.get("system", "").strip().split("\n", 1)[0])[:110]
        lines.append(f"- @{h} (kanalen: {','.join(c['channels'])}) — {first}")
    return "\n".join(lines)


def session_clause(cfg, handle, requester=None):
    """Wat deze agent zelf kan starten, verteld in zijn systemprompt.

    Zonder deze regel weet een agent niet dat werksessies bestaan: odin meldde
    2026-09-09 in #general (terecht) "ik heb geen tool-toegang tot een tmux-sessie
    op agent@agent-lxc". Dit vertelt hem wat hij WEL heeft. Het verruimt geen
    mandaat — wie welk type mag starten staat in sessions.yml en wordt daar
    afgedwongen; dit is alleen de aankondiging. `requester` = degene namens wie
    de agent zou starten; types die diegene niet mag, noemen we niet."""
    starters = (cfg or {}).get("types") or {}
    types = {n: t for n, t in starters.items()
             if handle in (t.get("starters") or [])
             # Ook de vrager moet het type mogen starten — anders kondigt de agent
             # een sessie aan die meteen een ⛔ krijgt.
             and (requester is None or requester in (t.get("starters") or []))}
    if not types:
        return ""
    lines = "\n".join(f"- `{n}` — {t.get('description') or t.get('workdir', '')}"
                     for n, t in sorted(types.items()))
    return ("\n\nJe kunt zelf een WERKSESSIE starten: een langere, LEZENDE claude-run "
            "met eigen gereedschap en eigen werkmap, die zijn resultaat in dit kanaal "
            "post. Zet daarvoor als LAATSTE regel van je antwoord precies:\n"
            "!sessie <type> <opdracht in een zin>\n"
            f"Beschikbare types:\n{lines}\n"
            "Doe dat alleen als het gevraagde werk echt uitzoeken vergt — voor een "
            "gesprek antwoord je zelf. Hoogstens één sessie per antwoord, en zeg in "
            "je eigen woorden dat je 'm start. Een sessie leest en stelt voor; hij "
            "verandert niets.")


def build_prompt(handle, chan, recent, trigger, pub2name):
    lines = [f"Kanaal #{chan}. Recente berichten:"]
    for m in recent:
        who = pub2name.get(m.get("pubkey", ""), "iemand")
        lines.append(f"{who}: {m.get('content','')}")
    lines.append("")
    lines.append(f"Je bent '{handle}'. Reageer als vervolg op het gesprek "
                 f"hierboven, op dit laatste bericht: {trigger!r}")
    return "\n".join(lines)


# Een geweigerde tool levert GEEN permission_denial op: hij is niet aanwezig, dus
# er valt niets te weigeren — de agent merkt het en zegt het in tekst. Daarom vragen
# we één machineleesbare regel, zodat de listener 'm per run naar #escalatie kan
# tillen i.p.v. dat een limitatie in een chatregel verdwijnt.
LIMIT_MARKER = "LIMITATIE:"
LIMIT_CLAUSE = (
    "\n\nAls je iets niet kunt doen omdat een tool ontbreekt of geweigerd wordt, "
    "begin je antwoord dan met één regel:\n"
    f"{LIMIT_MARKER} <wat je miste, in een halve zin>\n"
    "Daarna gewoon je antwoord. Gebruik die regel alleen daarvoor — niet voor "
    "inhoudelijke onzekerheid, en niet als je de vraag wél kon beantwoorden."
)
