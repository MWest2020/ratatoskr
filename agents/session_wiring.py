#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""De koppeling tussen een `!sessie`-marker en de sessie-register.

Apart van listener.py om dezelfde reden als destijds `chat/server.py`: dat
bestand zat op zijn regelgrens en groeide bij elke toevoeging verder. Deze twee
functies zijn bovendien geen luisterlogica — ze vertalen een marker naar een
start en een startbericht, en dat is goed los te testen.

`build(...)` geeft `(session_post, try_session)` terug, precies zoals de listener
ze gebruikte. De afhankelijkheden gaan erin in plaats van dat ze uit een module
komen, zodat een test geen relay, geen agents en geen SOPS nodig heeft.
"""
import sessions


def build(reg, agents, send, hub, log=print):
    """`(session_post, try_session)` voor deze listener-instantie."""

    def session_post(s, text):
        """Voortgang/resultaat onder de identiteit die het TYPE opgeeft."""
        c = agents.get(s["identity"])
        if c:
            send(s["cid"], text, c["nsec"], c["npub"])

    def try_session(text, starter, requester, cname, cid, message_id=""):
        """Voer een `!sessie`-marker uit. `starter` schreef de marker,
        `requester` is degene voor wie het gebeurt. Een weigering wordt gemeld en
        niet ingeslikt — stil weigeren ziet eruit als een sessie die niets vond."""
        mk = sessions.read_marker(text)
        if not mk:
            return
        type_name, task = mk
        s, reason = reg.start(type_name, task, starter, requester, cname, cid, message_id)
        if not s:
            log(f"[listener] sessie geweigerd ({starter}→{requester}/{type_name}): {reason}",
                flush=True)
            c = agents.get(hub) or next(iter(agents.values()))
            send(cid, f"⛔ no session: {reason}", c["nsec"], c["npub"])
            return
        on_behalf = "" if starter == requester else f" on behalf of @{requester}"
        log(f"[listener] sessie {type_name} gestart door {starter}{on_behalf} in #{cname}",
            flush=True)
        session_post(s, f"▶️ session `{type_name}` started by @{starter}{on_behalf} "
                        f"(max {s['max_s'] // 60} min) — "
                        f"task: {task[:120] or '(none)'}")

    return session_post, try_session
