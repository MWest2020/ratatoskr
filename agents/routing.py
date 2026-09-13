#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Doorsturen naar een ander kanaal, zonder een agent nieuwe macht te geven.

Aanleiding: Mark in #architectuur, 2026-09-13 — *"@odin zeg het tegen bouwer.
Jij bent hub, bouwer is spoke."* Odin kon dat niet: een agent antwoordt alleen in
het kanaal waar hij is aangesproken. Odin weigerde terecht het zichzelf te geven
(*"dat is een mandaatswijziging die door de handbook moet"*) en stelde
`route_message` voor. Mark ging akkoord, bouwer maakte er een change van en zette
er één voorwaarde bij: een security-run op twee punten — de payload versus een
instructie aan de agent, en een bronvermelding die vastligt.

**Geen tool, maar een marker.** Dezelfde vorm als `!sessie` (sessions.py), en om
dezelfde reden: de agent krijgt geen nieuwe rechten, geen tweede sleutel en geen
MCP-oppervlak. Hij schrijft een regel, de LISTENER doet het, en de listener is
code die je kunt lezen en testen. Een model dat een tool heeft, beslist zelf
wanneer hij hem gebruikt; een marker die de listener nakijkt, niet.

De twee punten van bouwer, allebei mechanisch afgedwongen:

1. **Letterlijk, en dat is te controleren.** De doorgestuurde tekst MOET woordelijk
   in het bericht van de mens staan dat deze beurt opriep. Kan de agent hem daar
   niet uithalen, dan gaat er niets weg. Dat is het verschil tussen "de agent
   belooft niet te interpreteren" en "de agent KAN niet interpreteren" — en alleen
   het tweede blijft waar als het model verandert.
2. **De bronvermelding komt uit de code.** Wie, uit welk kanaal, welk bericht. De
   agent schrijft die regel niet en kan hem niet weglaten of vervalsen.

En een derde die uit de rest volgt: welke kanalen een agent mag bereiken staat in
de handbook-definitie (`agent.chat.routes`), niet hier en niet in de prompt.
Leeg of afwezig = niets doorsturen. Fail-closed.
"""
import re

MARKER = re.compile(r"^!route\s+#?([a-z0-9_-]{1,40})\s*\n(.+)\Z", re.S | re.I | re.M)


def read_marker(text):
    """`(kanaal, payload)` of None. De payload is alles na de markerregel."""
    if not text:
        return None
    m = MARKER.search(text)
    if not m:
        return None
    payload = m.group(2).strip()
    return (m.group(1).lower(), payload) if payload else None


def strip_marker(text):
    """Het antwoord zonder de markerregel en zonder de payload.

    Wat overblijft is wat de agent tegen zijn eigen kanaal zegt. Zou de payload
    blijven staan, dan stond dezelfde tekst twee keer in twee kanalen en weet
    niemand meer welke de doorgestuurde is."""
    return MARKER.sub("", text or "").strip()


def _flat(s):
    """Witruimte genormaliseerd. Een model dat een regeleinde anders zet stuurt
    niet iets anders door; een model dat een WOORD verandert wel."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def verbatim(payload, source):
    """Staat `payload` woordelijk in `source`?

    Dit is de hele veiligheidsclaim. Zonder deze controle is "letterlijk
    doorsturen" een belofte in een systeemprompt, en een belofte in een prompt is
    precies zo sterk als het model van vandaag.
    """
    p, s = _flat(payload), _flat(source)
    return bool(p) and p in s


def allowed_channels(cfg):
    """De kanalen uit de handbook-definitie. Alles anders dan een lijst met
    strings telt als 'niets' — een verkeerd ingevuld veld mag geen rechten geven."""
    routes = (cfg or {}).get("routes")
    if not isinstance(routes, list):
        return []
    return [c.lower() for c in routes if isinstance(c, str) and c]


def may_route(cfg, channel, payload, source, channels):
    """`(True, "")` of `(False, reden)`. De reden is voor #escalatie: een
    geweigerde poging hoort zichtbaar te zijn, niet stil."""
    if channel not in channels:
        return False, f"kanaal #{channel} bestaat niet"
    toegestaan = allowed_channels(cfg)
    if channel not in toegestaan:
        return False, (f"mandaat staat #{channel} niet toe"
                       + (f" (wel: {', '.join(toegestaan)})" if toegestaan else " (geen routes)"))
    if not verbatim(payload, source):
        return False, "tekst staat niet woordelijk in het bericht van de mens"
    return True, ""


def provenance(human, from_channel, message_id):
    """De regel die de code schrijft en de agent niet.

    De lezer — mens of agent — moet zonder navragen weten dat dit doorgestuurd
    is, door wie en waarvandaan. Het bericht-id maakt het naspeurbaar: zonder dat
    is 'namens Mark' een bewering en geen verwijzing.
    """
    kort = (message_id or "")[:12]
    return (f"↪️ doorgestuurd namens **{human}** uit #{from_channel}"
            + (f" (bericht `{kort}`)" if kort else ""))


def routed_text(human, from_channel, message_id, payload):
    """Wat er in het doelkanaal komt te staan.

    De payload staat in een blockquote. Niet als opmaak: zo is voor de ontvangende
    agent zichtbaar waar andermans woorden beginnen en ophouden. De regel eronder
    zegt wat er van hem verwacht wordt, en dat die woorden niet van de doorstuurder
    zijn."""
    quote = "\n".join("> " + ln if ln else ">" for ln in payload.splitlines())
    return (provenance(human, from_channel, message_id) + "\n\n" + quote
            + f"\n\nBovenstaande is letterlijk overgenomen van {human}; "
              "de doorstuurder heeft er niets aan toegevoegd.")


def handle(answer, agent, cfg, cname, human, source, message_id, channels,
           send, here_cid):
    """Voer een `!route`-marker uit. Geeft het antwoord terug zonder de marker.

    `send(cid, text, nsec, npub)` is de poster van de listener — dezelfde als
    waarmee de agent zijn gewone antwoord plaatst, dus het doorgestuurde bericht
    draagt de handtekening van de doorstuurder en niet die van de mens. Een
    weigering gaat naar #escalatie, of naar dit kanaal als dat niet bestaat:
    stil weigeren is hoe je erachter komt dat niemand het merkt.
    """
    mk = read_marker(answer)
    if not mk:
        return answer
    channel, payload = mk
    rest = strip_marker(answer)
    post = lambda cid, text: send(cid, text, cfg["nsec"], cfg["npub"])  # noqa: E731
    ok, reden = may_route(cfg, channel, payload, source, channels)
    if not ok:
        post(channels.get("escalatie", here_cid),
             f"⛔ {agent} wilde doorsturen naar #{channel}: {reden}")
        return rest or f"(doorsturen naar #{channel} geweigerd: {reden})"
    post(channels[channel], routed_text(human, cname, message_id, payload))
    return rest or f"↪️ doorgestuurd naar #{channel}."
