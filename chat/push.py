# SPDX-License-Identifier: EUPL-1.2
"""Web Push — opslag van push-subscriptions (stdlib-only).

De VM-backend bewaart hier de subscriptions en serveert de VAPID-public-key; het
daadwerkelijke versturen gebeurt vanaf agent-lxc (orchestrator/push-notify.py, met
pywebpush) — de VM-backend blijft bewust dependency-loos.
"""
import json
import os
import threading

# Runtime-state, GEEN git-inhoud: op de VM zet chat.env PUSH_SUBS_PATH naar een
# state-dir buiten de deploy-checkout (/var/lib/boomhuis/push_subs.json). De
# default hier is enkel een lokale fallback voor tests; het bestand staat in
# .gitignore. Runbook: chat/README.md → "Web Push".
SUBS_PATH = os.environ.get(
    "PUSH_SUBS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_subs.json"))
# De subscribe-route is onbeschermd (tailnet-only, geen per-user auth). Cap het
# aantal subscriptions zodat een tailnet-node de opslag niet ongelimiteerd kan
# laten groeien; oudste valt eruit (FIFO).
MAX_SUBS = int(os.environ.get("PUSH_MAX_SUBS", "50"))
_lock = threading.Lock()


def vapid_public():
    return os.environ.get("VAPID_PUBLIC", "")


def _valid_sub(sub):
    """Een echte Web-Push-subscription: dict met een https-endpoint + p256dh/auth.

    Zonder deze poort accepteert /api/push/subscribe elk JSON-object; dit dwingt
    de vorm af die pywebpush ook echt kan versturen."""
    if not isinstance(sub, dict):
        return False
    ep = sub.get("endpoint")
    if not isinstance(ep, str) or not ep.startswith("https://") or len(ep) > 1024:
        return False
    keys = sub.get("keys")
    return isinstance(keys, dict) and bool(keys.get("p256dh")) and bool(keys.get("auth"))


def load_subscriptions():
    try:
        with open(SUBS_PATH) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write(subs):
    tmp = SUBS_PATH + ".tmp"
    # 0600: de subscriptions zijn per-apparaat push-tokens; net als chat.env
    # horen ze niet wereld-leesbaar (default umask geeft 0644).
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(subs, f)
    os.replace(tmp, SUBS_PATH)


def add_subscription(sub):
    """Voeg een subscription toe (dedup op endpoint). Return True bij succes."""
    if not _valid_sub(sub):
        return False
    ep = sub["endpoint"]
    with _lock:
        subs = [s for s in load_subscriptions() if s.get("endpoint") != ep]
        subs.append(sub)
        if len(subs) > MAX_SUBS:
            subs = subs[-MAX_SUBS:]
        _write(subs)
    return True
