# SPDX-License-Identifier: EUPL-1.2
# /// script
# dependencies = ["pywebpush>=1.14", "pyyaml>=6"]
# ///
"""Stuur een Web Push naar alle boomhuis-subscriptions (vanaf agent-lxc).

De VM bewaart de subscriptions (/var/lib/boomhuis/push_subs.json, buiten de
deploy-checkout); dit script leest ze via ssh en verstuurt met pywebpush + de
VAPID-private-key uit SOPS. De VM-backend blijft zo dependency-loos. Aanroep:
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
# Lezen/prunen van de subs gebeurt via één vastgepinde VM-helper (sudoers pint
# precies dit pad), zodat de sender geen `sudo sh`/`sudo python3 -c` — feitelijk
# een root-shell — nodig heeft. De helper draait als root en schrijft 0600.
SUBS_ADMIN = os.environ.get("PUSH_SUBS_ADMIN", "/usr/local/bin/boomhuis-push-subs")


def vapid():
    env = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))
    dec = subprocess.run(["sops", "-d", os.path.join(BOOMHUIS, "secrets", "vapid.yaml")],
                         capture_output=True, text=True, env=env)
    if dec.returncode != 0:
        sys.exit(f"[push] SOPS-decrypt vapid.yaml faalde: {dec.stderr[:200]}")
    return yaml.safe_load(dec.stdout)["vapid"]


def subscriptions():
    # De helper print de subs (of [] als er nog geen bestand is). Een gefaalde
    # ssh-hop (255), sudo-weigering of leesfout geeft rc != 0 — dat mag NIET als
    # "0 subs" doorgaan, anders meldt de sender vals succes terwijl er wél abonnees
    # zijn. Alleen een expliciete lege/[]-uitvoer is echt 0 subs.
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
    """Verwijder verlopen endpoints (404/410) via de VM-helper (race-veilig: de VM
    herleest zelf)."""
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
    ap.add_argument("--body", default=None, help="anders van stdin")
    a = ap.parse_args()
    body = a.body if a.body is not None else sys.stdin.read().strip()
    v = vapid()
    subs = subscriptions()
    if not subs:
        print("[push] geen subscriptions — niets te versturen."); return
    payload = json.dumps({"title": a.title, "body": body[:300], "url": a.url})
    # Per abonnee de push-service noemen. "1/1 verstuurd" zegt niets over WELK
    # toestel; een fcm.googleapis.com-endpoint is Chrome (Android of desktop),
    # web.push.apple.com is Safari/iOS. Waargenomen 2026-09-08: één abonnement,
    # FCM, HTTP 201 — en toch niets op de iPhone, want die had zich nooit
    # aangemeld. Zonder deze regel is dat onzichtbaar.
    for s_ in subs:
        host = (s_.get("endpoint") or "").split("/")[2:3]
        print(f"[push] abonnee: {host[0] if host else '?'}")
    sent = 0
    dead = []
    for s in subs:
        ep = s.get("endpoint") or ""
        try:
            # Urgency high + een TTL van een uur. Waargenomen 2026-09-08: twee
            # pushes kwamen pas veel later en tegelijk aan op een Android-toestel.
            # Zonder Urgency-header behandelt de push-service een bericht als
            # "normal" en mag hij het vasthouden tot het toestel uit doze komt.
            # Voor een chatbericht is dat het verkeerde gedrag: te laat is hier
            # hetzelfde als niet. De TTL begrenst de andere kant — een melding van
            # gisteren wil je niet alsnog.
            r = webpush(subscription_info=s, data=payload, vapid_private_key=v["private"],
                        vapid_claims={"sub": v.get("subject", "mailto:boomhuis@localhost")},
                        ttl=3600, headers={"Urgency": "high"})
            # De statuscode erbij: 201 betekent "de push-service heeft 'm
            # aangenomen", NIET "het toestel heeft 'm getoond". Dat onderscheid
            # kostte een half uur zoeken.
            print(f"[push] {ep.split('/')[2]}: HTTP {getattr(r, 'status_code', '?')} (aangenomen "
                  f"door de push-service; aflevering is niet te bevestigen)")
            sent += 1
        except WebPushException as e:
            # 404/410 = de push-service kent dit endpoint niet meer → weg ermee.
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                dead.append(ep)
            print(f"[push] sub faalde ({ep[:40]}): {e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 — één kapotte sub (bv. ongeldige
            # keys) mag de rest van de batch nooit meesleuren.
            print(f"[push] sub-fout ({ep[:40]}): {type(e).__name__}: {e}", file=sys.stderr)
    prune(dead)
    print(f"[push] verstuurd naar {sent}/{len(subs)} subscription(s)")


if __name__ == "__main__":
    main()
