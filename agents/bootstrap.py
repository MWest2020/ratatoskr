# SPDX-License-Identifier: EUPL-1.2
"""Opstart-helpers voor de listener: YAML-lezers en de handbook-def-parser. Apart
zodat listener.py onder de ≤200-regel-conventie blijft. Puur: paden en urls komen
als parameters binnen, geen module-globals van de listener.
"""
import os
import re
import urllib.request

import yaml


def load_yaml(path):
    return yaml.safe_load(open(path))


def load_channels(root):
    return {n: c["id"] for n, c in load_yaml(os.path.join(root, "channels.yml"))["channels"].items()}


def load_identity_npubs(root):
    d = load_yaml(os.path.join(root, "identities.yml"))["identities"]
    return {h: v.get("npub") for h, v in d.items()}, {v["pubkey_hex"]: h for h, v in d.items()}


def fetch_def(base, handle):
    """Haal de canonieke definitie uit de handbook. Return {npub, channels,
    system, provider} of None bij falen (fail-closed)."""
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
    channels = chat.get("channels") or []  # `or`: vangt óók `channels:` = YAML null
    # systemprompt = de blockquote onder '## Chat-facet'
    body = s[m.end():]
    cf = re.search(r"##\s*Chat-facet.*?\n(.*?)(?:\n##\s|\Z)", body, re.S)
    system = ""
    if cf:
        system = "\n".join(
            ln[2:] if ln.startswith("> ") else ln[1:] if ln.startswith(">") else ""
            for ln in cf.group(1).splitlines() if ln.startswith(">")
        ).strip()
    provider = (fm.get("provider") or "claude-p")
    # Model en tools komen uit de registry en worden afgedwongen (besluit Mark
    # 2026-09-06). Fail-closed: zonder model draait de agent niet — anders valt hij
    # stil terug op de omgevingsdefault en weet niemand waarop hij draaide.
    tools = chat.get("tools") or {}
    return {"npub": fm.get("npub"), "channels": channels, "system": system,
            "provider": provider, "model": chat.get("model") or "",
            "allow": tools.get("allow") or [], "deny": tools.get("deny") or [],
            "skills": chat.get("skills") or []}


def build_agents(cfg, base, npubs):
    """De agents die deze listener draait: definitie uit de handbook, nsec uit env,
    npub gelijk aan de registry, en een model in de def. Elk van die vier is
    fail-closed — een agent die er niet doorheen komt draait niet, met de reden op
    stdout. Zonder de model-check zou hij stil op de omgevingsdefault draaien."""
    agents = {}
    for handle in cfg.get("run", []):
        nsec = os.environ.get("NSEC_" + handle.upper(), "")
        if not nsec:
            print(f"[listener] {handle}: geen NSEC_ in env — overslaan", flush=True)
            continue
        d = fetch_def(base, handle)
        if not d:
            print(f"[listener] {handle}: geen handbook-definitie — NIET gespawnd", flush=True)
            continue
        if d["npub"] != npubs.get(handle):
            print(f"[listener] {handle}: npub wijkt af van registry — NIET gespawnd", flush=True)
            continue
        if not d.get("model"):
            print(f"[listener] {handle}: geen `model` in de definitie — NIET gespawnd", flush=True)
            continue
        agents[handle] = {**d, "nsec": nsec}
    return agents
