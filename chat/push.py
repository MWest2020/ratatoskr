# SPDX-License-Identifier: MIT
"""Web Push — storage of push subscriptions (stdlib only).

The VM backend keeps the subscriptions here and serves the VAPID public key; the
actual sending happens from agent-lxc (orchestrator/push-notify.py, with
pywebpush) — the VM backend stays deliberately dependency-free.
"""
import json
import os
import threading

# Runtime state, NOT git content: on the VM chat.env points PUSH_SUBS_PATH at a
# state dir outside the deploy checkout (/var/lib/boomhuis/push_subs.json). The
# default here is only a local fallback for tests; the file is in .gitignore.
# Runbook: chat/README.md → "Web Push".
SUBS_PATH = os.environ.get(
    "PUSH_SUBS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_subs.json"))
# The subscribe route is unprotected (tailnet only, no per-user auth). Cap the
# number of subscriptions so a tailnet node cannot grow the storage without
# limit; the oldest drops out (FIFO).
MAX_SUBS = int(os.environ.get("PUSH_MAX_SUBS", "50"))
_lock = threading.Lock()


def vapid_public():
    return os.environ.get("VAPID_PUBLIC", "")


def _clean_sub(sub):
    """Validate a Web Push subscription and return it NORMALISED (endpoint plus
    keys.p256dh/auth only), or None. Without this gate /api/push/subscribe accepts
    any JSON object and stores it unfiltered; this enforces the shape pywebpush can
    actually send and bounds every field by length."""
    if not isinstance(sub, dict):
        return None
    ep = sub.get("endpoint")
    if not isinstance(ep, str) or not ep.startswith("https://") or len(ep) > 1024:
        return None
    keys = sub.get("keys")
    if not isinstance(keys, dict):
        return None
    p, a = keys.get("p256dh"), keys.get("auth")
    if not (isinstance(p, str) and 0 < len(p) <= 256 and isinstance(a, str) and 0 < len(a) <= 256):
        return None
    return {"endpoint": ep, "keys": {"p256dh": p, "auth": a}}


def load_subscriptions():
    try:
        with open(SUBS_PATH) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write(subs):
    # The state dir may be missing (fresh VM, skipped mkdir step): create it
    # instead of an unhandled FileNotFoundError through do_POST (a traceback, no
    # HTTP answer).
    d = os.path.dirname(SUBS_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = SUBS_PATH + ".tmp"
    # 0600: the subscriptions are per-device push tokens; like chat.env they do
    # not belong world-readable (the default umask gives 0644).
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(subs, f)
    os.replace(tmp, SUBS_PATH)


def add_subscription(sub):
    """Add a subscription (deduped on endpoint). Returns True on success."""
    clean = _clean_sub(sub)
    if clean is None:
        return False
    ep = clean["endpoint"]
    with _lock:
        subs = [s for s in load_subscriptions() if s.get("endpoint") != ep]
        subs.append(clean)
        if len(subs) > MAX_SUBS:
            subs = subs[-MAX_SUBS:]
        _write(subs)
    return True
