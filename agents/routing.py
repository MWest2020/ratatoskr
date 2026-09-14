#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Een bericht doorsturen naar een ander kanaal, zoals Slack dat doet.

Aanleiding: Mark in #architectuur, 2026-09-13 — *"@odin zeg het tegen bouwer.
Jij bent hub, bouwer is spoke."* Een agent antwoordt alleen in het kanaal waar
hij is aangesproken, en odin weigerde terecht het zichzelf te geven.

**Waarom dit de tweede versie is.** De eerste eiste dat de doorgestuurde tekst
WOORDELIJK in het bericht van de mens stond. Dat klonk streng en was verkeerd
gericht: het gebruik is niet "papegaai Mark na" maar "geef deze bevinding door,
met duiding". Op 2026-09-14 schreef odin precies zo'n bericht voor @bouwer — een
gecontroleerde analyse van vier securitybevindingen — en mijn regel had het
geweigerd. Mark: *"en mogelijk gewoon doorsturen zoals in slack?"*

Slack-stijl is bovendien VEILIGER, niet losser. Je stuurt een BESTAAND bericht
door, op id, en de listener haalt de inhoud zelf op uit het kanaal. De agent
schrijft het citaat dus niet — hij wijst het aan. Dat is een sterkere garantie
dan een woordelijkheidscontrole: die controleert of een kopie klopt, dit maakt
kopiëren overbodig. Wat de agent er zelf bij zegt staat eronder, zichtbaar van
hem.

De grenzen die blijven:
- **Alleen kanalen uit `agent.chat.routes`** in de handbook-definitie. Leeg,
  afwezig of van het verkeerde type = niets doorsturen. Fail-closed.
- **Alleen een bericht uit DIT kanaal.** Een agent kan niet iets uit een kanaal
  doorsturen waar hij niet is aangesproken; hij kent het immers niet.
- **De bronvermelding komt uit de code.** Wie het schreef, in welk kanaal, met
  welk id. De agent schrijft die regel niet en kan hem niet weglaten.
"""
import re

MARKER = re.compile(r"^!(?:forward|route)\s+#?([a-z0-9_-]{1,40})\s+([0-9a-f]{8,64})"
                    r"[ \t]*(?:\n(.*))?\Z", re.S | re.I | re.M)


def read_marker(text):
    """`(kanaal, bericht_id, eigen_notitie)` of None.

    `!route` blijft werken als alias: agents die de oude vorm geleerd hebben
    moeten niet stilletjes falen omdat ik het woord veranderd heb.
    """
    if not text:
        return None
    m = MARKER.search(text)
    if not m:
        return None
    return m.group(1).lower(), m.group(2).lower(), (m.group(3) or "").strip()


def strip_marker(text):
    """Het antwoord zonder de markerregel en zonder de eigen notitie.

    Wat overblijft is wat de agent tegen zijn eigen kanaal zegt. Zou de notitie
    blijven staan, dan stond dezelfde tekst in twee kanalen en weet niemand meer
    welke de doorgestuurde is."""
    return MARKER.sub("", text or "").strip()


def allowed_channels(cfg):
    """De kanalen uit de handbook-definitie. Alles anders dan een lijst met
    strings telt als 'niets' — een verkeerd ingevuld veld mag geen rechten
    geven."""
    routes = (cfg or {}).get("routes")
    if not isinstance(routes, list):
        return []
    return [c.lower() for c in routes if isinstance(c, str) and c]


def find_message(berichten, bericht_id):
    """Het bericht met dit id uit DIT kanaal, of None.

    Een prefix volstaat: een agent die een id overtypt uit wat hij op zijn
    scherm ziet, heeft meestal niet alle 64 tekens. Meerdere treffers op
    hetzelfde voorvoegsel geven None — dan is het geen aanwijzing maar een gok.
    """
    treffers = [m for m in (berichten or [])
                if str(m.get("id", "")).lower().startswith(bericht_id)]
    return treffers[0] if len(treffers) == 1 else None


def may_forward(cfg, channel, channels):
    """`(True, "")` of `(False, reden)`. De reden is voor #escalatie: een
    geweigerde poging hoort zichtbaar te zijn, niet stil."""
    if channel not in channels:
        return False, f"kanaal #{channel} bestaat niet"
    toegestaan = allowed_channels(cfg)
    if channel not in toegestaan:
        return False, (f"mandaat staat #{channel} niet toe"
                       + (f" (wel: {', '.join(toegestaan)})" if toegestaan else " (geen routes)"))
    return True, ""


def forwarded_text(schrijver, from_channel, bericht, agent, notitie):
    """Wat er in het doelkanaal komt te staan.

    De inhoud in een blockquote, zodat voor de ontvangende agent zichtbaar is
    waar andermans woorden beginnen en ophouden. De notitie van de doorstuurder
    staat eronder en draagt zijn naam, zodat niemand hem voor het origineel
    aanziet — dat onderscheid is het hele punt van doorsturen.
    """
    inhoud = (bericht.get("content") or "").strip()
    kort = str(bericht.get("id", ""))[:12]
    kop = (f"↪️ doorgestuurd uit #{from_channel} · oorspronkelijk van **{schrijver}**"
           + (f" · `{kort}`" if kort else ""))
    quote = "\n".join("> " + ln if ln else ">" for ln in inhoud.splitlines())
    uit = kop + "\n\n" + quote
    if notitie:
        uit += f"\n\n**{agent}** erbij: {notitie}"
    return uit


def handle(answer, agent, cfg, cname, berichten, namen, channels, send, here_cid):
    """Voer een `!forward`-marker uit. Geeft het antwoord terug zonder de marker.

    `berichten` = de berichten van dit kanaal (de listener heeft ze al), `namen`
    = pubkey -> handle. `send(cid, text, nsec, npub)` is de poster van de
    listener: het doorgestuurde bericht draagt dus de handtekening van de
    DOORSTUURDER en niet die van de oorspronkelijke schrijver.
    """
    mk = read_marker(answer)
    if not mk:
        return answer
    channel, bericht_id, notitie = mk
    rest = strip_marker(answer)

    def post(cid, tekst):
        return send(cid, tekst, cfg["nsec"], cfg["npub"])

    def weiger(reden):
        post(channels.get("escalatie", here_cid),
             f"⛔ {agent} wilde doorsturen naar #{channel}: {reden}")
        return rest or f"(doorsturen naar #{channel} geweigerd: {reden})"

    ok, reden = may_forward(cfg, channel, channels)
    if not ok:
        return weiger(reden)
    bericht = find_message(berichten, bericht_id)
    if bericht is None:
        # Niet gevonden of dubbelzinnig. Beide betekenen: de agent wijst niet
        # eenduidig iets aan, en dan sturen we niets door.
        return weiger(f"geen eenduidig bericht met id `{bericht_id}` in dit kanaal")
    schrijver = namen.get(bericht.get("pubkey", ""), "iemand")
    post(channels[channel], forwarded_text(schrijver, cname, bericht, agent, notitie))
    return rest or f"↪️ doorgestuurd naar #{channel}."
