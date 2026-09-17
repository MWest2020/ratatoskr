# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["pywebpush>=1.14", "pyyaml>=6"]
# ///
"""Send a Web Push to every boomhuis subscription (from agent-lxc).

The VM keeps the subscriptions (/var/lib/boomhuis/push_subs.json, outside the
deploy checkout); this script reads them over ssh and sends with pywebpush plus
the VAPID private key from SOPS. That keeps the VM backend dependency-free. Call
it as:
  uv run orchestrator/push-notify.py --title "PR #7" --url / --body "verdict: FAIL"
  echo "message" | uv run orchestrator/push-notify.py --title "Boomhuis"
"""
import argparse
import json
import os
import subprocess
import sys

from pywebpush import webpush, WebPushException
import yaml

BOOMHUIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Reading and pruning the subs goes through one pinned VM helper (sudoers pins
# exactly this path), so the sender needs no `sudo sh`/`sudo python3 -c` — which
# is effectively a root shell. The helper runs as root and writes 0600.
SUBS_ADMIN = os.environ.get("PUSH_SUBS_ADMIN", "/usr/local/bin/boomhuis-push-subs")


def vapid():
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "vapid.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[push] SOPS-decrypt vapid.yaml faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)["vapid"]


def subscriptions():
    # The helper prints the subs (or [] when there is no file yet). A failed ssh
    # hop (255), a sudo refusal or a read error gives rc != 0 — that must NOT pass
    # as "0 subs", otherwise the sender reports false success while there are
    # subscribers. Only an explicitly empty or [] output is really 0 subs.
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
                        "sudo", "-n", SUBS_ADMIN, "read"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[push] subs lezen op buzz-relay faalde (rc={r.returncode}): "
                 f"{(r.stderr or r.stdout).strip()[:200]}")
    raw = (r.stdout or "").strip()
    if raw in ("", "[]"):
        return []
    try:
        d = json.loads(raw)
    except ValueError:
        sys.exit(f"[push] push_subs.json is corrupt (kon niet parsen): {raw[:120]}")
    return d if isinstance(d, list) else []


def prune(dead):
    """Remove expired endpoints (404/410) through the VM helper (race-safe: the VM
    re-reads by itself)."""
    if not dead:
        return
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
                        "sudo", "-n", SUBS_ADMIN, "prune"],
                       input=json.dumps(list(dead)), capture_output=True, text=True)
    if r.returncode == 0:
        print(f"[push] {len(dead)} verlopen subscription(s) opgeruimd")
    else:
        print(f"[push] opruimen faalde (rc={r.returncode}): {(r.stderr or r.stdout).strip()[:120]}",
              file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="Boomhuis")
    ap.add_argument("--url", default="/")
    ap.add_argument("--body", default=None, help="otherwise read from stdin")
    a = ap.parse_args()
    body = a.body if a.body is not None else sys.stdin.read().strip()
    v = vapid()
    subs = subscriptions()
    if not subs:
        print("[push] geen subscriptions — niets te versturen."); return
    payload = json.dumps({"title": a.title, "body": body[:300], "url": a.url})
    # Name the push service per subscriber. "1/1 sent" says nothing about WHICH
    # device; an fcm.googleapis.com endpoint is Chrome (Android or desktop),
    # web.push.apple.com is Safari/iOS. Observed 2026-09-08: one subscription,
    # FCM, HTTP 201 — and still nothing on the iPhone, because it had never
    # subscribed. Without this line that is invisible.
    for s_ in subs:
        host = (s_.get("endpoint") or "").split("/")[2:3]
        print(f"[push] abonnee: {host[0] if host else '?'}")
    sent = 0
    dead = []
    for s in subs:
        ep = s.get("endpoint") or ""
        try:
            # Urgency high plus a TTL of an hour. Observed 2026-09-08: two pushes
            # arrived much later and at the same time on an Android device.
            # Without an Urgency header the push service treats a message as
            # "normal" and may hold it until the device leaves doze. For a chat
            # message that is the wrong behaviour: too late is the same as never.
            # The TTL bounds the other side — you do not want yesterday's
            # notification after all.
            r = webpush(subscription_info=s, data=payload, vapid_private_key=v["private"],
                        vapid_claims={"sub": v.get("subject", "mailto:boomhuis@localhost")},
                        ttl=3600, headers={"Urgency": "high"})
            # The status code with it: 201 means "the push service accepted it",
            # NOT "the device showed it". That distinction cost half an hour of
            # searching.
            print(f"[push] {ep.split('/')[2]}: HTTP {getattr(r, 'status_code', '?')} (aangenomen "
                  f"door de push-service; aflevering is niet te bevestigen)")
            sent += 1
        except WebPushException as e:
            # 404/410 = the push service no longer knows this endpoint → drop it.
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                dead.append(ep)
            print(f"[push] sub faalde ({ep[:40]}): {e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 — one broken sub (e.g. invalid
            # keys) must never drag the rest of the batch down with it.
            print(f"[push] sub-fout ({ep[:40]}): {type(e).__name__}: {e}", file=sys.stderr)
    prune(dead)
    print(f"[push] verstuurd naar {sent}/{len(subs)} subscription(s)")


if __name__ == "__main__":
    main()
