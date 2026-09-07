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

Invariant: conversatie-only. Geen shell/repo/dispatch vanuit hier.
"""
import json
import os
import subprocess
import time

import bootstrap
import prompts
import providers
import reporting
import topology

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8


CHANNELS = bootstrap.load_channels(ROOT)
NPUBS, PUB2NAME = bootstrap.load_identity_npubs(ROOT)
CFG = bootstrap.load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Actieve agent-set: def uit de handbook + nsec uit env + npub-match + model.
AGENTS = bootstrap.build_agents(CFG, BASE, NPUBS)

AGENT_PUBS = set()  # gevuld met pubkeys van agents (uit identities via naam)


def buzz_env(nsec):
    e = dict(os.environ)
    e["BUZZ_PRIVATE_KEY"] = nsec
    e["BUZZ_RELAY_URL"] = RELAY
    return e


def get_messages(cid, nsec):
    """Berichten oplopend gesorteerd. None bij een MISLUKTE read (rc!=0/timeout/
    onparsebaar), [] bij een echt LEEG kanaal — niet verwarren (anders wordt een
    gefaalde read 'geseed' en volgt historie-spam)."""
    try:
        p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                           env=buzz_env(nsec), capture_output=True, text=True, timeout=25)
    except Exception:  # timeout/OSError = mislukte read (None), mag de daemon niet doden
        return None
    if p.returncode != 0:
        return None
    try:
        d = json.loads(p.stdout)
    except Exception:
        return None
    msgs = d if isinstance(d, list) else d.get("messages", [])
    return sorted(msgs, key=lambda m: m.get("created_at", 0))


def send(cid, content, nsec, self_npub):
    """Post een antwoord (eigen npub als --mention → @woorden blijven presentation-
    only). True bij succes; een geweigerde send loggen we (geen valse 'antwoordde')."""
    try:
        p = subprocess.run([BUZZ, "messages", "send", "--channel", cid, "--content", "-",
                            "--mention", self_npub],
                           env=buzz_env(nsec), input=content, capture_output=True, text=True, timeout=25)
    except Exception as e:  # timeout/OSError mag de daemon niet doden
        print(f"[listener] send-fout in {cid}: {e}", flush=True)
        return False
    if p.returncode != 0:
        print(f"[listener] send FAALDE in {cid}: {(p.stderr or p.stdout).strip()[:120]}", flush=True)
    return p.returncode == 0


def buzz_run(nsec):
    """`run(args) -> stdout|""`-callable voor topology.py (buzz-env van deze agent;
    faalt de call → lege string, topology valt dan terug)."""
    def run(args):
        try:
            p = subprocess.run([BUZZ, *args], env=buzz_env(nsec),
                               capture_output=True, text=True, timeout=25)
        except Exception:  # timeout/OSError → lege string (belofte houdt, poll crasht niet)
            return ""
        return p.stdout if p.returncode == 0 else ""
    return run


def main():
    if not AGENTS:
        raise SystemExit("geen agents gespawnd (geen bron/nsec/npub-match)")
    # Reader = coordinator (lid van elk kanaal via default+backfill) zodat list/
    # members/messages álle kanalen zien; één agent-sleutel mist private kanalen.
    if "coordinator" not in AGENTS:
        print("[listener] LET OP: geen coordinator gespawnd — reader valt terug op "
              f"{next(iter(AGENTS))}, mogelijk smallere kanaal-zichtbaarheid", flush=True)
    read_nsec = (AGENTS.get("coordinator") or next(iter(AGENTS.values())))["nsec"]
    run = buzz_run(read_nsec)  # relay-I/O voor topology (kanalen + leden)
    # pubkeys van agents, om niet op agents te reageren
    name2pub = {h: p for p, h in PUB2NAME.items()}
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
        msgs = get_messages(cid, read_nsec)
        if msgs is not None:
            seed(cid, msgs)
    print(f"[listener] actief; agents uit handbook: {', '.join(AGENTS)}", flush=True)
    while True:
        for cname, cid in topology.poll_channels(run, CHANNELS).items():
            msgs = get_messages(cid, read_nsec)
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
                if m.get("pubkey") in AGENT_PUBS:
                    continue
                content = m.get("content", "")
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
                    if handle == "coordinator":
                        p = prompts.roster_text(AGENTS) + "\n\n" + p
                        lt = prompts.live_text(ROOT)
                        if lt:
                            p = lt + "\n\n" + p
                    try:
                        r = providers.run(cfg.get("provider"),
                                          cfg["system"] + prompts.LIMIT_CLAUSE, p,
                                          model=cfg.get("model"), allow=cfg.get("allow"),
                                          deny=cfg.get("deny"),
                                          progress=reporting.progress_poster(
                                              send, cid, cfg, handle))
                    except Exception as e:  # incl. time-out: de beurt mag nooit klappen
                        r = {"answer": f"(fout: {e})", "error": str(e)[:120]}
                    ans = r.get("answer", "(geen antwoord)")
                    if send(cid, ans, cfg["nsec"], cfg["npub"]):
                        print(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
                    reporting.report_run(send, CHANNELS, handle, cname, cfg, r)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
