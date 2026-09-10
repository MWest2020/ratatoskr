# SPDX-License-Identifier: EUPL-1.2
"""Relay-I/O: lezen en posten via de buzz-cli. Apart van listener.py zodat die
onder de ≤200-regel-conventie blijft en de sessie-code dezelfde send kan gebruiken.

Belofte van dit bestand: een storing (time-out, OSError, rc≠0) doodt de daemon
nooit, maar wordt ook nooit als "leeg" verkocht — een MISLUKTE read geeft None,
een echt leeg kanaal geeft [].
"""
import json
import os
import subprocess

BUZZ = os.environ.get("BUZZ_BIN", "buzz")


def buzz_env(nsec, relay):
    e = dict(os.environ)
    e["BUZZ_PRIVATE_KEY"] = nsec
    e["BUZZ_RELAY_URL"] = relay
    return e


def get_messages(cid, nsec, relay):
    """Berichten oplopend gesorteerd. None bij een MISLUKTE read (rc!=0/timeout/
    onparsebaar), [] bij een echt LEEG kanaal — niet verwarren (anders wordt een
    gefaalde read 'geseed' en volgt historie-spam)."""
    try:
        p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                           env=buzz_env(nsec, relay), capture_output=True,
                           text=True, timeout=25)
    except Exception:  # timeout/OSError = mislukte read (None), mag de daemon niet doden
        return None
    if p.returncode != 0:
        return None
    try:
        d = json.loads(p.stdout)
    except Exception:
        return None
    msgs = d if isinstance(d, list) else d.get("messages", [])
    return sorted(msgs, key=lambda m: m.get("created_at", 0))


def sender(relay):
    """Geeft `send(cid, content, nsec, npub) -> bool`, zoals de listener en
    reporting.py hem verwachten (eigen npub als --mention → @woorden blijven
    presentation-only). Een geweigerde send loggen we: geen valse 'antwoordde'."""
    def send(cid, content, nsec, self_npub):
        try:
            p = subprocess.run([BUZZ, "messages", "send", "--channel", cid,
                                "--content", "-", "--mention", self_npub],
                               env=buzz_env(nsec, relay), input=content,
                               capture_output=True, text=True, timeout=25)
        except Exception as e:  # timeout/OSError mag de daemon niet doden
            print(f"[listener] send-fout in {cid}: {e}", flush=True)
            return False
        if p.returncode != 0:
            print(f"[listener] send FAALDE in {cid}: "
                  f"{(p.stderr or p.stdout).strip()[:120]}", flush=True)
        return p.returncode == 0
    return send


def runner(nsec, relay):
    """`run(args) -> stdout|""`-callable voor topology.py (buzz-env van deze
    identiteit; faalt de call → lege string, topology valt dan terug)."""
    def run(args):
        try:
            p = subprocess.run([BUZZ, *args], env=buzz_env(nsec, relay),
                               capture_output=True, text=True, timeout=25)
        except Exception:  # timeout/OSError → lege string (belofte houdt, poll crasht niet)
            return ""
        return p.stdout if p.returncode == 0 else ""
    return run
