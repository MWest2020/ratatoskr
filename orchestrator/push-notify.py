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


SUBS_REMOTE = "/opt/buzz-build/chat/push_subs.json"


def subscriptions():
    # `|| true` maakt een ontbrekend bestand (nog geen subs) tot exit 0 met lege
    # output; een écht gefaalde ssh-hop geeft 255 — dat mag NIET als "0 subs"
    # doorgaan, anders meldt de sender vals succes.
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "buzz-relay",
                        f"cat {SUBS_REMOTE} 2>/dev/null || true"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[push] ssh naar buzz-relay faalde (rc={r.returncode}): {r.stderr.strip()[:200]}")
    try:
        d = json.loads(r.stdout or "[]")
        return d if isinstance(d, list) else []
    except ValueError:
        return []


def prune(dead):
    """Verwijder verlopen endpoints (404/410) remote, atomair, race-veilig: de VM
    herleest het bestand zelf zodat een gelijktijdige aanmelding niet sneuvelt."""
    if not dead:
        return
    remote = (
        "python3 - <<'PY'\n"
        "import json,os,sys\n"
        f"p={SUBS_REMOTE!r}\n"
        "dead=set(json.loads(sys.stdin.read()))\n"
        "try:\n"
        "    subs=json.load(open(p))\n"
        "except Exception:\n"
        "    sys.exit(0)\n"
        "keep=[s for s in subs if s.get('endpoint') not in dead]\n"
        "fd=os.open(p+'.tmp',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)\n"
        "os.write(fd,json.dumps(keep).encode()); os.close(fd); os.replace(p+'.tmp',p)\n"
        "PY"
    )
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "buzz-relay", remote],
                       input=json.dumps(list(dead)), capture_output=True, text=True)
    if r.returncode == 0:
        print(f"[push] {len(dead)} verlopen subscription(s) opgeruimd")
    else:
        print(f"[push] opruimen faalde (rc={r.returncode}): {r.stderr.strip()[:120]}", file=sys.stderr)


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
    dead = []
    for s in subs:
        try:
            webpush(subscription_info=s, data=payload, vapid_private_key=v["private"],
                    vapid_claims={"sub": v.get("subject", "mailto:boomhuis@localhost")})
            sent += 1
        except WebPushException as e:
            ep = s.get("endpoint") or ""
            # 404/410 = de push-service kent dit endpoint niet meer → weg ermee.
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                dead.append(ep)
            print(f"[push] sub faalde ({ep[:40]}): {e}", file=sys.stderr)
    prune(dead)
    print(f"[push] verstuurd naar {sent}/{len(subs)} subscription(s)")


if __name__ == "__main__":
    main()
