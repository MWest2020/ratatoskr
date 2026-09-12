# SPDX-License-Identifier: EUPL-1.2
"""Relay I/O: reading and posting through the buzz CLI. Separate from
listener.py so that file stays under the ≤200-line convention and the session
code can use the same send.

The promise of this file: a failure (timeout, OSError, rc≠0) never kills the
daemon, but is never sold as "empty" either — a FAILED read returns None, a
genuinely empty channel returns [].
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
    """Messages sorted ascending. None on a FAILED read (rc!=0/timeout/
    unparsable), [] on a genuinely EMPTY channel — do not confuse the two
    (otherwise a failed read gets 'seeded' and history spam follows)."""
    try:
        p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                           env=buzz_env(nsec, relay), capture_output=True,
                           text=True, timeout=25)
    except Exception:  # timeout/OSError = failed read (None); must not kill the daemon
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
    """Returns `send(cid, content, nsec, npub) -> bool`, as the listener and
    reporting.py expect it (own npub as --mention → @words stay
    presentation-only). A refused send is logged: no false 'answered'."""
    def send(cid, content, nsec, self_npub):
        try:
            p = subprocess.run([BUZZ, "messages", "send", "--channel", cid,
                                "--content", "-", "--mention", self_npub],
                               env=buzz_env(nsec, relay), input=content,
                               capture_output=True, text=True, timeout=25)
        except Exception as e:  # timeout/OSError must not kill the daemon
            print(f"[listener] send-fout in {cid}: {e}", flush=True)
            return False
        if p.returncode != 0:
            print(f"[listener] send FAALDE in {cid}: "
                  f"{(p.stderr or p.stdout).strip()[:120]}", flush=True)
        return p.returncode == 0
    return send


def runner(nsec, relay):
    """`run(args) -> stdout|""` callable for topology.py (buzz env of this
    identity; if the call fails → empty string, topology then falls back)."""
    def run(args):
        try:
            p = subprocess.run([BUZZ, *args], env=buzz_env(nsec, relay),
                               capture_output=True, text=True, timeout=25)
        except Exception:  # timeout/OSError → empty string (promise holds, poll survives)
            return ""
        return p.stdout if p.returncode == 0 else ""
    return run
