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
import re
import subprocess
import time
import urllib.request

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUZZ = os.environ.get("BUZZ_BIN", "buzz")
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8
MAX_TURN_S = 150


def load_yaml(path):
    return yaml.safe_load(open(path))


def load_channels():
    return {n: c["id"] for n, c in load_yaml(os.path.join(ROOT, "channels.yml"))["channels"].items()}


def load_identity_npubs():
    d = load_yaml(os.path.join(ROOT, "identities.yml"))["identities"]
    return {h: v.get("npub") for h, v in d.items()}, {v["pubkey_hex"]: h for h, v in d.items()}


def fetch_def(base, handle):
    """Haal de canonieke definitie uit de handbook. Return {npub, channels,
    system} of None bij falen (fail-closed)."""
    url = f"{base}/{handle}.md"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            s = r.read().decode("utf-8")
    except Exception as e:
        print(f"[listener] def {handle} niet te laden: {e}", flush=True)
        return None
    m = re.match(r"^---\n(.*?)\n---", s, re.S)
    if not m:
        return None
    fm = yaml.safe_load(m.group(1)).get("agent", {})
    chat = fm.get("chat") or {}
    channels = chat.get("channels", [])
    # systemprompt = de blockquote onder '## Chat-facet'
    body = s[m.end():]
    cf = re.search(r"##\s*Chat-facet.*?\n(.*?)(?:\n##\s|\Z)", body, re.S)
    system = ""
    if cf:
        system = "\n".join(
            ln[2:] if ln.startswith("> ") else ln[1:] if ln.startswith(">") else ""
            for ln in cf.group(1).splitlines() if ln.startswith(">")
        ).strip()
    return {"npub": fm.get("npub"), "channels": channels, "system": system}


CHANNELS = load_channels()
NPUBS, PUB2NAME = load_identity_npubs()
CFG = load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Bouw de actieve agent-set: def uit handbook + nsec uit env + npub-match.
AGENTS = {}
for handle in CFG.get("run", []):
    nsec = os.environ.get("NSEC_" + handle.upper(), "")
    if not nsec:
        print(f"[listener] {handle}: geen NSEC_ in env — overslaan", flush=True)
        continue
    d = fetch_def(BASE, handle)
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


def ask_claude(system, prompt):
    p = subprocess.run([CLAUDE, "-p", "--append-system-prompt", system, prompt],
                       capture_output=True, text=True, timeout=MAX_TURN_S)
    return (p.stdout or "").strip() or "(geen antwoord)"


def roster_text():
    """Korte samenvatting van de huidige vloot — context voor de coordinator."""
    lines = ["Huidige agent-vloot (uit de handbook-registry):"]
    for h, c in AGENTS.items():
        if h == "coordinator":
            continue
        first = (c.get("system", "").strip().split("\n", 1)[0])[:110]
        lines.append(f"- @{h} (kanalen: {','.join(c['channels'])}) — {first}")
    return "\n".join(lines)


def build_prompt(handle, chan, recent, trigger):
    lines = [f"Kanaal #{chan}. Recente berichten:"]
    for m in recent:
        who = PUB2NAME.get(m.get("pubkey", ""), "iemand")
        lines.append(f"{who}: {m.get('content','')}")
    lines.append("")
    lines.append(f"Je bent '{handle}'. Reageer als vervolg op het gesprek "
                 f"hierboven, op dit laatste bericht: {trigger!r}")
    return "\n".join(lines)


def main():
    if not AGENTS:
        raise SystemExit("geen agents gespawnd (geen bron/nsec/npub-match)")
    read_nsec = next(iter(AGENTS.values()))["nsec"]
    # pubkeys van agents, om niet op agents te reageren
    name2pub = {h: p for p, h in PUB2NAME.items()}
    for h in AGENTS:
        AGENT_PUBS.add(name2pub.get(h))
    seen = set()
    for cid in CHANNELS.values():
        for m in get_messages(cid, read_nsec):
            seen.add(m.get("id"))
    print(f"[listener] actief; agents uit handbook: {', '.join(AGENTS)}", flush=True)
    while True:
        for cname, cid in CHANNELS.items():
            msgs = get_messages(cid, read_nsec)
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                if m.get("pubkey") in AGENT_PUBS:
                    continue
                content = m.get("content", "")
                # Wie moet reageren? (a) expliciete @mentions van hier-gescopte
                # agents; (b) anders thread-continuïteit: de laatst-actieve agent
                # in dit kanaal (binnen ~10 berichten) praat door zonder mention.
                targets = [h for h, cfg in AGENTS.items()
                           if cname in cfg["channels"]
                           and ("@" + h).lower() in content.lower()]
                reason = "mention"
                if not targets:
                    for prev in reversed(msgs[max(0, i - 10):i]):
                        if prev.get("pubkey") in AGENT_PUBS:
                            h = PUB2NAME.get(prev.get("pubkey"))
                            if h in AGENTS and cname in AGENTS[h]["channels"]:
                                targets = [h]
                                reason = "vervolg"
                            break  # alleen de meest recente agent telt
                for handle in targets:
                    cfg = AGENTS[handle]
                    print(f"[listener] {reason} @{handle} in #{cname}: {content[:50]}", flush=True)
                    recent = msgs[max(0, i - MAX_CTX):i + 1]
                    p = build_prompt(handle, cname, recent, content)
                    if handle == "coordinator":
                        p = roster_text() + "\n\n" + p
                    try:
                        ans = ask_claude(cfg["system"], p)
                    except subprocess.TimeoutExpired:
                        ans = "(time-out — vraag te zwaar voor een chatbeurt)"
                    except Exception as e:
                        ans = f"(fout: {e})"
                    send(cid, ans, cfg["nsec"], cfg["npub"])
                    print(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
