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
import topology

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8
MAX_TURN_S = 150


CHANNELS = bootstrap.load_channels(ROOT)
NPUBS, PUB2NAME = bootstrap.load_identity_npubs(ROOT)
CFG = bootstrap.load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Bouw de actieve agent-set: def uit handbook + nsec uit env + npub-match.
AGENTS = {}
for handle in CFG.get("run", []):
    nsec = os.environ.get("NSEC_" + handle.upper(), "")
    if not nsec:
        print(f"[listener] {handle}: geen NSEC_ in env — overslaan", flush=True)
        continue
    d = bootstrap.fetch_def(BASE, handle)
    if not d:
        print(f"[listener] {handle}: geen handbook-definitie — NIET gespawnd", flush=True)
        continue
    if d["npub"] != NPUBS.get(handle):
        print(f"[listener] {handle}: npub wijkt af van registry — NIET gespawnd", flush=True)
        continue
    AGENTS[handle] = {**d, "nsec": nsec}

AGENT_PUBS = set()  # gevuld met pubkeys van agents (uit identities via naam)


def buzz_env(nsec):
    e = dict(os.environ)
    e["BUZZ_PRIVATE_KEY"] = nsec
    e["BUZZ_RELAY_URL"] = RELAY
    return e


def get_messages(cid, nsec):
    p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                       env=buzz_env(nsec), capture_output=True, text=True, timeout=25)
    if p.returncode != 0:
        return []
    try:
        d = json.loads(p.stdout)
    except Exception:
        return []
    msgs = d if isinstance(d, list) else d.get("messages", [])
    return sorted(msgs, key=lambda m: m.get("created_at", 0))


def send(cid, content, nsec, self_npub):
    # Eigen npub als --mention: dat staat willekeurige @woorden in het antwoord
    # toe als presentation-only (buzz weigert anders onbekende @mentions).
    subprocess.run([BUZZ, "messages", "send", "--channel", cid, "--content", "-",
                    "--mention", self_npub],
                   env=buzz_env(nsec), input=content, capture_output=True, text=True, timeout=25)


# Protocol-naad: het agent-backend zit achter één functie. Vandaag 'claude-p'
# (sub-first). Een nieuw backend = één extra tak; de handbook-def declareert de
# provider (front-matter agent.provider, default claude-p).
def run_provider(provider, system, prompt):
    if provider in (None, "claude-p", "claude"):
        p = subprocess.run([CLAUDE, "-p", "--append-system-prompt", system, prompt],
                           capture_output=True, text=True, timeout=MAX_TURN_S)
        return (p.stdout or "").strip() or "(geen antwoord)"
    # hier pluggen toekomstige backends in (codex, remote-agent, http/SSE-connector…)
    return f"(provider '{provider}' nog niet ondersteund door deze listener)"


def buzz_run(nsec):
    """Geeft een `run(args) -> stdout|""`-callable voor topology.py, met de
    buzz-env van deze agent. Faalt de call, dan lege string (topology valt terug)."""
    def run(args):
        p = subprocess.run([BUZZ, *args], env=buzz_env(nsec),
                           capture_output=True, text=True, timeout=25)
        return p.stdout if p.returncode == 0 else ""
    return run


def main():
    if not AGENTS:
        raise SystemExit("geen agents gespawnd (geen bron/nsec/npub-match)")
    read_nsec = next(iter(AGENTS.values()))["nsec"]
    run = buzz_run(read_nsec)  # relay-I/O voor topology (kanalen + leden)
    # pubkeys van agents, om niet op agents te reageren
    name2pub = {h: p for p, h in PUB2NAME.items()}
    for h in AGENTS:
        AGENT_PUBS.add(name2pub.get(h))

    def scoped(h, cname, cid):
        """Reageert agent h in dit kanaal? Handbook-scope OF relay-lid (union)."""
        return cname in AGENTS[h]["channels"] or name2pub.get(h) in topology.members(run, cid)

    seen = set()
    for cid in topology.poll_channels(run, CHANNELS).values():
        for m in get_messages(cid, read_nsec):
            seen.add(m.get("id"))
    print(f"[listener] actief; agents uit handbook: {', '.join(AGENTS)}", flush=True)
    while True:
        for cname, cid in topology.poll_channels(run, CHANNELS).items():
            msgs = get_messages(cid, read_nsec)
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                if m.get("pubkey") in AGENT_PUBS:
                    continue
                content = m.get("content", "")
                # Wie moet reageren? (a) expliciete @mentions van agents die hier
                # gescopt of relay-lid zijn; (b) anders thread-continuïteit: de
                # laatst-actieve agent in dit kanaal (binnen ~10 berichten) praat door.
                targets = [h for h in AGENTS
                           if ("@" + h).lower() in content.lower() and scoped(h, cname, cid)]
                reason = "mention"
                if not targets:
                    for prev in reversed(msgs[max(0, i - 10):i]):
                        if prev.get("pubkey") in AGENT_PUBS:
                            h = PUB2NAME.get(prev.get("pubkey"))
                            if h in AGENTS and scoped(h, cname, cid):
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
                        ans = run_provider(cfg.get("provider"), cfg["system"], p)
                    except subprocess.TimeoutExpired:
                        ans = "(time-out — vraag te zwaar voor een chatbeurt)"
                    except Exception as e:
                        ans = f"(fout: {e})"
                    send(cid, ans, cfg["nsec"], cfg["npub"])
                    print(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
