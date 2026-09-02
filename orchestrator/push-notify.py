# SPDX-License-Identifier: EUPL-1.2
# /// script
# dependencies = ["pywebpush>=1.14", "pyyaml>=6"]
# ///
"""Stuur een Web Push naar alle boomhuis-subscriptions (vanaf agent-lxc).

De VM bewaart de subscriptions (chat/push_subs.json); dit script leest ze via ssh
en verstuurt met pywebpush + de VAPID-private-key uit SOPS. De VM-backend blijft
zo dependency-loos. Aanroep:
  uv run orchestrator/push-notify.py --title "PR #7" --url / --body "verdict: FAIL"
  echo "bericht" | uv run orchestrator/push-notify.py --title "Boomhuis"
"""
import argparse
import json
import os
import subprocess
import sys

from pywebpush import webpush, WebPushException
import yaml

BOOMHUIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def vapid():
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "vapid.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[push] SOPS-decrypt vapid.yaml faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)["vapid"]


def subscriptions():
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
                        "cat /opt/buzz-build/chat/push_subs.json 2>/dev/null || echo []"],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout or "[]")
        return d if isinstance(d, list) else []
    except ValueError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="Boomhuis")
    ap.add_argument("--url", default="/")
    ap.add_argument("--body", default=None, help="anders van stdin")
    a = ap.parse_args()
    body = a.body if a.body is not None else sys.stdin.read().strip()
    v = vapid()
    subs = subscriptions()
    if not subs:
        print("[push] geen subscriptions — niets te versturen."); return
    payload = json.dumps({"title": a.title, "body": body[:300], "url": a.url})
    sent = 0
    for s in subs:
        try:
            webpush(subscription_info=s, data=payload, vapid_private_key=v["private"],
                    vapid_claims={"sub": v.get("subject", "mailto:boomhuis@localhost")})
            sent += 1
        except WebPushException as e:
            print(f"[push] sub faalde ({(s.get('endpoint') or '')[:40]}): {e}", file=sys.stderr)
    print(f"[push] verstuurd naar {sent}/{len(subs)} subscription(s)")


if __name__ == "__main__":
    main()
