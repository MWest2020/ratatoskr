# SPDX-License-Identifier: MIT
"""Start-up helpers for the listener: YAML readers and the handbook def parser.
Separate so listener.py stays under the ≤200-line convention. Pure: paths and
urls come in as parameters, no module globals from the listener.
"""
import fcntl
import os
import urllib.request

import yaml

import readshell
from defparse import parse_def  # re-exported: tests and callers use bootstrap.parse_def


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


def load_channel_defaults(root):
    """`{channel: handle}` for channels that name a default agent.

    Separate from `load_channels` so the shape that everything else depends on
    (`{name: id}`) stays what it is. A channel without the key is not in here,
    which is the normal case: this is opt-in per channel, never a global
    default. A feed like #statistics that answers every line would be noise
    with a price tag.
    """
    d = load_yaml(os.path.join(root, "channels.yml"))["channels"]
    return {n: c["default_agent"] for n, c in d.items() if c.get("default_agent")}


def check_channel_defaults(defaults, agents):
    """Raise when a default agent cannot actually speak in its channel.

    Fail loudly at startup, not silently at the first message. A default that
    is skipped because the agent is not scoped there looks exactly like a
    listener that is not running -- and this repo already pays for that class
    of failure elsewhere.
    """
    for cname, handle in sorted(defaults.items()):
        cfg = agents.get(handle)
        if cfg is None:
            raise ValueError(
                f"channels.yml: #{cname} names default_agent '{handle}', "
                f"which is not an agent in the handbook")
        if cname not in (cfg.get("channels") or []):
            raise ValueError(
                f"channels.yml: #{cname} names default_agent '{handle}', but "
                f"that agent's definition does not list #{cname} in chat.channels")


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
    """The parsed handbook definition, or None (fail-closed). After a merge,
    raw.githubusercontent.com caches ~5 minutes and its nodes disagree: wait
    until THIS function sees the change, several times in a row, then restart
    (docs/how-to/read-shell.md)."""
    url = f"{base}/{handle}.md"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            s = r.read().decode("utf-8")
    except Exception as e:
        print(f"[listener] def {handle} niet te laden: {e}", flush=True)
        return None
    return parse_def(s)


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
        if not d.get("system"):
            # Without a system prompt the agent only knows its name: the failure
            # that went unseen from 2026-09-22 to 2026-10-22.
            print(f"[listener] {handle}: no system prompt (no blockquote under "
                  "'## Chat facet') — NOT spawned", flush=True)
            continue
        stray = readshell.stray_bash(d.get("allow"))
        if stray:
            # A chat turn gets no free shell (change odin-read-shell): only the
            # read shell, and a one-word edit to a definition must not change that.
            print(f"[listener] {handle}: Bash other than the read shell ({stray}) — NOT spawned",
                  flush=True)
            continue
        if readshell.RULE in d.get("allow", []) and "Bash" in d.get("deny", []):
            print(f"[listener] {handle}: read shell allowed but Bash denied — deny wins, "
                  "the shell will not work", flush=True)
        agents[handle] = {**d, "nsec": nsec}
    return agents
