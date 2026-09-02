# SPDX-License-Identifier: EUPL-1.2
"""Web Push — opslag van push-subscriptions (stdlib-only).

De VM-backend bewaart hier de subscriptions en serveert de VAPID-public-key; het
daadwerkelijke versturen gebeurt vanaf agent-lxc (orchestrator/push-notify.py, met
pywebpush) — de VM-backend blijft bewust dependency-loos.
"""
import json
import os
import threading

SUBS_PATH = os.environ.get(
    "PUSH_SUBS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_subs.json"))
_lock = threading.Lock()


def vapid_public():
    return os.environ.get("VAPID_PUBLIC", "")


def load_subscriptions():
    try:
        with open(SUBS_PATH) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def add_subscription(sub):
    """Voeg een subscription toe (dedup op endpoint). Return True bij succes."""
    if not isinstance(sub, dict) or not sub.get("endpoint"):
        return False
    ep = sub["endpoint"]
    with _lock:
        subs = [s for s in load_subscriptions() if s.get("endpoint") != ep]
        subs.append(sub)
        tmp = SUBS_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(subs, f)
        os.replace(tmp, SUBS_PATH)
    return True
