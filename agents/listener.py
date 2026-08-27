#!/usr/bin/env python3
"""Boomhuis chat-agents — multi-agent listener rond claude -p (sub-first).

Config-gedreven: rollen/kanalen/systemprompts in agents.yml, pubkeys in
identities.yml, privésleutels via env NSEC_<HANDLE> (de launcher haalt ze uit
SOPS). Per @handle-mention in een gescoped kanaal draait claude -p met de
systemprompt van die agent en post het antwoord terug, getekend met de
sleutel van die agent.

Invariant: conversatie-only. Geen shell/repo/dispatch vanuit hier.
"""
import json
import os
import subprocess
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8
MAX_TURN_S = 150


def load_channels():
    d = yaml.safe_load(open(os.path.join(ROOT, "channels.yml")))
    return {n: c["id"] for n, c in d["channels"].items()}


def load_identities():
    d = yaml.safe_load(open(os.path.join(ROOT, "identities.yml")))
    return {h: v["pubkey_hex"] for h, v in d["identities"].items()}


def load_agents():
    d = yaml.safe_load(open(os.path.join(HERE, "agents.yml")))
    return d["agents"]


CHANNELS = load_channels()                 # name -> id
PUBKEYS = load_identities()                # handle -> pubkey
NAMES = {pub: h for h, pub in PUBKEYS.items()}  # pubkey -> naam
AGENTS = load_agents()                     # handle -> {rol, channels, system}
# handle -> nsec uit env (launcher exporteert NSEC_<HANDLE>)
NSEC = {h: os.environ.get("NSEC_" + h.upper(), "") for h in AGENTS}
AGENT_PUBS = {PUBKEYS.get(h) for h in AGENTS}


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


def send(cid, content, nsec):
    subprocess.run([BUZZ, "messages", "send", "--channel", cid, "--content", "-"],
                   env=buzz_env(nsec), input=content, capture_output=True,
                   text=True, timeout=25)


def ask_claude(system, prompt):
    p = subprocess.run([CLAUDE, "-p", "--append-system-prompt", system, prompt],
                       capture_output=True, text=True, timeout=MAX_TURN_S)
    return (p.stdout or "").strip() or "(geen antwoord)"


def build_prompt(handle, chan, recent, trigger):
    lines = [f"Kanaal #{chan}. Recente berichten:"]
    for m in recent:
        who = NAMES.get(m.get("pubkey", ""), "iemand")
        lines.append(f"{who}: {m.get('content','')}")
    lines.append("")
    lines.append(f"Je bent '{handle}', genoemd met @{handle}. Reageer op: "
                 f"{trigger!r}")
    return "\n".join(lines)


def main():
    # gebruik één agent-nsec om te lezen (lezen mag elk lid)
    read_nsec = next((n for n in NSEC.values() if n), None)
    if not read_nsec:
        raise SystemExit("geen agent-nsec in env (NSEC_<HANDLE>)")
    seen = set()
    for cid in CHANNELS.values():
        for m in get_messages(cid, read_nsec):
            seen.add(m.get("id"))
    active = [h for h in AGENTS if NSEC.get(h)]
    print(f"[listener] actief; agents: {', '.join(active)}", flush=True)
    while True:
        for cname, cid in CHANNELS.items():
            msgs = get_messages(cid, read_nsec)
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                if m.get("pubkey") in AGENT_PUBS:
                    continue  # niet op agents (incl. jezelf) reageren
                content = m.get("content", "")
                for handle, cfg in AGENTS.items():
                    if not NSEC.get(handle):
                        continue
                    if cname not in cfg.get("channels", []):
                        continue
                    if ("@" + handle).lower() not in content.lower():
                        continue
                    print(f"[listener] @{handle} in #{cname}: {content[:50]}",
                          flush=True)
                    recent = msgs[max(0, i - MAX_CTX):i + 1]
                    try:
                        ans = ask_claude(cfg["system"],
                                         build_prompt(handle, cname, recent, content))
                    except subprocess.TimeoutExpired:
                        ans = "(time-out — vraag te zwaar voor een chatbeurt)"
                    except Exception as e:
                        ans = f"(fout: {e})"
                    send(cid, ans, NSEC[handle])
                    print(f"[listener] {handle} antwoordde in #{cname}", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
