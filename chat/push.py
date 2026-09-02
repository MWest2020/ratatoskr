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


def _clean_sub(sub):
    """Valideer een Web-Push-subscription en geef 'm GENORMALISEERD terug (alleen
    endpoint + keys.p256dh/auth), of None. Zonder deze poort accepteert
    /api/push/subscribe elk JSON-object en slaat het ongefilterd op; dit dwingt de
    vorm af die pywebpush echt kan versturen en begrenst elk veld op lengte."""
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
    tmp = SUBS_PATH + ".tmp"
    # 0600: de subscriptions zijn per-apparaat push-tokens; net als chat.env
    # horen ze niet wereld-leesbaar (default umask geeft 0644).
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(subs, f)
    os.replace(tmp, SUBS_PATH)


def add_subscription(sub):
    """Voeg een subscription toe (dedup op endpoint). Return True bij succes."""
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
