# SPDX-License-Identifier: EUPL-1.2
"""Start-up helpers for the listener: YAML readers and the handbook def parser.
Separate so listener.py stays under the ≤200-line convention. Pure: paths and
urls come in as parameters, no module globals from the listener.
"""
import fcntl
import os
import re
import urllib.request

import yaml


def only_me(path="/tmp/boomhuis-listener.lock"):
    """One listener per host, or nothing. Returns the open lock file (which you
    must hold on to) or None when one is already running.

    Why: two listeners answer every message twice and start every work session
    twice. Measured 2026-09-11 — one `!sessie` marker in #architectuur, two
    sessions. The cause was a restart that killed only one of the two processes;
    this makes that impossible instead of unlikely. The lock disappears by itself
    when the process stops (flock, not a pidfile that survives a kill)."""
    f = open(path, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    f.write(str(os.getpid()) + "\n")
    f.flush()
    return f


def load_yaml(path):
    return yaml.safe_load(open(path))


def load_channels(root):
    return {n: c["id"] for n, c in load_yaml(os.path.join(root, "channels.yml"))["channels"].items()}


def load_identity_npubs(root):
    d = load_yaml(os.path.join(root, "identities.yml"))["identities"]
    return {h: v.get("npub") for h, v in d.items()}, {v["pubkey_hex"]: h for h, v in d.items()}


def hub_handle(root):
    """The hub agent: the ACTIVE identity with role `meta-agent`, or None.

    By role, not by name. Until 2026-09-07 the hub was called `coordinator` and
    is now `odin`; three places in the listener still used the old name and
    silently fell back on another agent. The role is the stable property, and a
    revoked key does not count."""
    d = load_yaml(os.path.join(root, "identities.yml"))["identities"]
    return next((h for h, v in d.items()
                 if v.get("rol") == "meta-agent" and v.get("status") == "actief"), None)


def fetch_def(base, handle):
    """Fetch the canonical definition from the handbook. Returns {npub, channels,
    system, provider} or None on failure (fail-closed)."""
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
    channels = chat.get("channels") or []  # `or` also catches `channels:` = YAML null
    # system prompt = the blockquote under '## Chat-facet'
    body = s[m.end():]
    cf = re.search(r"##\s*Chat-facet.*?\n(.*?)(?:\n##\s|\Z)", body, re.S)
    system = ""
    if cf:
        system = "\n".join(
            ln[2:] if ln.startswith("> ") else ln[1:] if ln.startswith(">") else ""
            for ln in cf.group(1).splitlines() if ln.startswith(">")
        ).strip()
    provider = (fm.get("provider") or "claude-p")
    # Model and tools come from the registry and are enforced (Mark's decision,
    # 2026-09-06). Fail-closed: without a model the agent does not run — otherwise
    # it silently falls back on the environment default and nobody knows what it
    # ran on.
    tools = chat.get("tools") or {}
    # `routes` = de kanalen waar deze agent de woorden van de mens naartoe mag
    # doorsturen (routing.py). Uit de handbook, net als de rest van het mandaat:
    # zo staat het recht op één plek en niet in een prompt of een lokale yaml.
    return {"npub": fm.get("npub"), "channels": channels, "system": system,
            "provider": provider, "model": chat.get("model") or "",
            "allow": tools.get("allow") or [], "deny": tools.get("deny") or [],
            "routes": chat.get("routes") or [],
            "skills": chat.get("skills") or []}


def build_agents(cfg, base, npubs):
    """The agents this listener runs: definition from the handbook, nsec from the
    environment, npub matching the registry, and a model in the def. Each of those
    four is fail-closed — an agent that does not pass does not run, with the
    reason on stdout. Without the model check it would silently run on the
    environment default."""
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
