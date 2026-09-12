#!/usr/bin/env python3
"""Boomhuis chat-agents — multi-agent listener rond claude -p (sub-first).

De agent-DEFINITIES (systemprompt/chat-facet, kanalen, npub) komen uit de
HANDBOOK (single source of truth): docs/agents/<naam>.md, opgehaald via raw.
`agents.yml` zegt alleen WELKE agents deze instantie draait; privésleutels
komen via env NSEC_<HANDLE> (uit SOPS).

Guardrail: een agent wordt alleen gedraaid als (a) z'n definitie uit de
handbook geladen kan worden en (b) de npub daarin overeenkomt met de identiteit
in identities.yml. Geen bron → geen spawn (fail-closed). De closed relay is de
achtervang op identiteitsniveau.

Invariant: geen shell, geen repo-schrijfrecht, geen dispatch vanuit hier. Een
`!sessie`-marker start wél een LEZENDE werksessie (zie sessions.py) — die verandert
niets en levert tekst in het kanaal.
"""
import os
import time

import bootstrap
import relay
import sessions
import prompts
import notify
import providers
import reporting
import topology

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8


CHANNELS = bootstrap.load_channels(ROOT)
NPUBS, PUB2NAME = bootstrap.load_identity_npubs(ROOT)
HUB = bootstrap.hub_handle(ROOT)   # rol meta-agent; None = geen hub gespawnd
ME_NAME = (os.environ.get("RATATOSKR_HUMAN")
           or os.environ.get("BOOMHUIS_HUMAN", "mark"))  # eigen berichten pushen niet
CFG = bootstrap.load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Actieve agent-set: def uit de handbook + nsec uit env + npub-match + model.
AGENTS = bootstrap.build_agents(CFG, BASE, NPUBS)

AGENT_PUBS = set()  # gevuld met pubkeys van agents (uit identities via naam)


def main():
    # Vasthouden zolang de listener leeft: sluiten geeft het slot vrij.
    lock = bootstrap.only_me()            # noqa: F841 — de referentie ís de functie
    if lock is None:
        # Exitcode 0, geen fout: onder systemd met `Restart=on-failure` zou een
        # niet-nul exit een herstartlus van 10 seconden opleveren tegen een slot
        # dat nooit vrijkomt. "Er draait er al een" is de gewenste uitkomst.
        print("[listener] er draait al een listener op deze host — gestopt "
              "(twee listeners = elk bericht dubbel)", flush=True)
        return
    if not AGENTS:
        raise SystemExit("geen agents gespawnd (geen bron/nsec/npub-match)")
    # Reader = de ORCHESTRATOR: die bezit elk kanaal en ziet ze dus allemaal
    # (gemeten 2026-09-07: orchestrator 15/15, assistent 8/15, de hub 4/15).
    read_nsec = os.environ.get("NSEC_ORCHESTRATOR", "").strip()
    if not read_nsec:
        raise SystemExit("[listener] NSEC_ORCHESTRATOR ontbreekt (zie agents/run.sh)")
    send = relay.sender(RELAY)
    fetch = lambda cid: relay.get_messages(cid, read_nsec, RELAY)  # noqa: E731
    run = relay.runner(read_nsec, RELAY)  # relay-I/O voor topology
    reg = sessions.Register(sessions.load(HERE))

    def session_post(s, text):
        """Voortgang/resultaat onder de identiteit die het TYPE declareert."""
        c = AGENTS.get(s["identity"])
        if c:
            send(s["cid"], text, c["nsec"], c["npub"])

    def try_session(text, starter, requester, cname, cid, message_id=""):
        """Een `!sessie`-marker uitvoeren. `starter` schreef de marker, `requester`
        is degene namens wie het gaat. Weigeringen worden gemeld, niet ingeslikt —
        een stille weigering lijkt op een sessie die niets vond."""
        mk = sessions.read_marker(text)
        if not mk:
            return
        type_name, task = mk
        s, reason = reg.start(type_name, task, starter, requester, cname, cid, message_id)
        if not s:
            print(f"[listener] sessie geweigerd ({starter}→{requester}/{type_name}): {reason}",
                  flush=True)
            c = AGENTS.get(HUB) or next(iter(AGENTS.values()))
            send(cid, f"⛔ geen sessie: {reason}", c["nsec"], c["npub"])
            return
        on_behalf = "" if starter == requester else f" namens @{requester}"
        print(f"[listener] sessie {type_name} gestart door {starter}{on_behalf} in #{cname}",
              flush=True)
        session_post(s, f"▶️ sessie `{type_name}` gestart door @{starter}{on_behalf} "
                        f"(max {s['max_s'] // 60} min) — "
                        f"opdracht: {task[:120] or '(geen)'}")

    reporting.report_missing_memberships(run, AGENTS, CHANNELS, PUB2NAME)
    name2pub = {h: p for p, h in PUB2NAME.items()}   # om niet op agents te reageren
    for h in AGENTS:
        AGENT_PUBS.add(name2pub.get(h))

    def scoped(h, cname, cid):  # mention-scope: handbook OF relay-lid (pure is_scoped)
        return topology.is_scoped(AGENTS[h]["channels"], cname, name2pub.get(h),
                                  lambda: topology.members(run, cid))  # lui: alleen bij need

    seen, seeded = set(), set()

    def seed(cid, msgs):
        # Historie van een (nieuw) kanaal als gezien markeren. Alleen bij een
        # GESLAAGDE read (msgs≠None) — anders 'geseed' + historie-spam.
        for m in msgs:
            seen.add(m.get("id"))
        seeded.add(cid)

    for cid in topology.poll_channels(run, CHANNELS).values():
        msgs = fetch(cid)
        if msgs is not None:
            seed(cid, msgs)
    print(f"[listener] actief; agents uit handbook: {', '.join(AGENTS)}", flush=True)
    while True:
        for cname, cid in topology.poll_channels(run, CHANNELS).items():
            msgs = fetch(cid)
            if msgs is None:      # mislukte read → overslaan, volgende tick opnieuw
                continue
            if cid not in seeded:  # kanaal net in de poll-set: historie als 'gezien'
                seed(cid, msgs)    # markeren, NIET op oude berichten reageren
                continue
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if not mid or mid in seen:  # id-loos bericht overslaan (niet dedup-baar)
                    continue
                seen.add(mid)
                # Melden vóór de agent-filter: juist een agent-ANTWOORD is waar
                # een mens op wacht. Wat níet meldt, beslist notify.wil_melden.
                writer = PUB2NAME.get(m.get("pubkey"), "?")
                if notify.should_notify(cname, writer, m.get("content", ""), ME_NAME):
                    notify.push(cname, writer, m.get("content", ""))
                if m.get("pubkey") in AGENT_PUBS:
                    continue
                content = m.get("content", "")
                # Mens typt de marker zelf: starter en requester zijn gelijk.
                try_session(content, writer, writer, cname, cid, mid)
                # (a) @mentions van hier-gescopte/relay-lid-agents; (b) anders: vervolg.
                targets = [h for h in AGENTS
                           if prompts.mentioned(content, h) and scoped(h, cname, cid)]
                reason = "mention"
                if not targets:
                    for prev in reversed(msgs[max(0, i - 10):i]):
                        if prev.get("pubkey") in AGENT_PUBS:
                            h = PUB2NAME.get(prev.get("pubkey"))
                            # vervolg (zonder mention) blijft def-kanaal-only (spec);
                            # membership verbreedt alléén de mention-tak hierboven.
                            if h in AGENTS and cname in AGENTS[h]["channels"]:
                                targets = [h]
                                reason = "vervolg"
                            break  # alleen de meest recente agent telt
                for handle in targets:
                    cfg = AGENTS[handle]
                    print(f"[listener] {reason} @{handle} in #{cname}: {content[:50]}", flush=True)
                    recent = msgs[max(0, i - MAX_CTX):i + 1]
                    p = prompts.build_prompt(handle, cname, recent, content, PUB2NAME)
                    know = prompts.channel_knowledge(ROOT, cname)
                    if know:
                        p = f"Kanaal-kennis (#{cname}):\n{know}\n\n" + p
                    if handle == HUB:
                        p = prompts.roster_text(AGENTS, HUB) + "\n\n" + p
                        lt = prompts.live_text(ROOT)
                        if lt:
                            p = lt + "\n\n" + p
                    try:
                        r = providers.run(cfg.get("provider"),
                                          cfg["system"] + prompts.LIMIT_CLAUSE
                                          + prompts.session_clause(reg.cfg, handle,
                                                                   writer), p,
                                          model=cfg.get("model"), allow=cfg.get("allow"),
                                          deny=cfg.get("deny"),
                                          progress=reporting.progress_poster(
                                              send, cid, cfg, handle))
                    except Exception as e:  # incl. time-out: de beurt mag nooit klappen
                        r = {"answer": f"(fout: {e})", "error": str(e)[:120]}
                    ans = r.get("answer", "(geen antwoord)")
                    mk = sessions.read_marker(ans)
                    text = sessions.strip_marker(ans) if mk else ans
                    if text and send(cid, text, cfg["nsec"], cfg["npub"]):
                        print(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
                    if mk:
                        # Odin schreef de marker, maar de vraag kwam van `writer`.
                        try_session(ans, handle, writer, cname, cid, mid)
                    reporting.report_run(send, CHANNELS, handle, cname, cfg, r)
        reg.tick(session_post)  # voortgang/afronding van lopende werksessies
        time.sleep(POLL)


if __name__ == "__main__":
    main()
