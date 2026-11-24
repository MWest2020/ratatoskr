# SPDX-License-Identifier: MIT
"""The checks of create-session-identity.py, pure, so they can be tested
without keys, SOPS or a relay.

Every value that ends up in an ssh argv or a buzz call is checked here first:
ssh joins its arguments into one remote shell line, so an unchecked
`pubkey_hex` from identities.yml would be a command on buzz-relay.

These checks stop mistakes and a tampered registry. They are not the gate:
the relay phase is Mark's step, and the permission layer plus Mark running it
is what decides. The script only refuses to do the wrong thing when asked.
"""
import re

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
PUB_RE = re.compile(r"^[0-9a-f]{64}$")
PHASES = ("registry", "relay", "all")


class Refused(Exception):
    """A reason to stop; the message says which."""


def check_name(name):
    if not NAME_RE.match(name or ""):
        raise Refused(f"name {name!r} must match {NAME_RE.pattern}")
    return name


def check_phase(phase, owner_step):
    """registry is the default and an agent's step. relay and all touch the
    relay and channel membership: Mark's step, so they need --owner-step."""
    if phase not in PHASES:
        raise Refused(f"unknown phase {phase!r}")
    if phase != "registry" and not owner_step:
        raise Refused(f"--phase {phase} is Mark's step (relay + channel membership, "
                      "signed by the orchestrator key): rerun with --owner-step")
    return phase


def channel_ids(names, chans):
    """[(name, id)], #escalatie first and always. #general is the hub channel
    (odin alone, spec identity-registry) and is refused, as ping.sh refuses a
    session there. A channel not in channels.yml, or archived, is refused."""
    if "general" in names:
        raise Refused("#general is hub-only (odin); a session is never a member")
    out = []
    for n in ["escalatie"] + [n for n in names if n != "escalatie"]:
        c = chans.get(n) or {}
        if not c.get("id"):
            raise Refused(f"channel {n!r} is not in channels.yml")
        if c.get("archived"):
            raise Refused(f"channel {n!r} is archived")
        out.append((n, c["id"]))
    return out


def relay_target(name, registry, secrets, derive):
    """(pubkey_hex, nsec) of an existing, active session identity, or Refused.

    `derive(secret_entry)` returns the pubkey hex the secret actually belongs
    to (or None when privkey_hex and nsec disagree). The registry pubkey must
    be 64 lowercase hex and equal that derived key: the registry is a git file
    anyone with a PR can change, the SOPS key is not."""
    e = registry.get(name)
    if not e:
        raise Refused(f"{name!r} is not in identities.yml: run --phase registry first")
    if e.get("rol") != "sessie":
        raise Refused(f"{name!r} has rol {e.get('rol')!r}: only a session identity (sessie)")
    if e.get("status") != "actief":
        raise Refused(f"{name!r} has status {e.get('status')!r}: only an active identity")
    pub = e.get("pubkey_hex")
    if not isinstance(pub, str) or not PUB_RE.match(pub):
        raise Refused(f"{name!r}: pubkey_hex is not 64 lowercase hex")
    s = secrets.get(name)
    if not s or not s.get("nsec") or not s.get("privkey_hex"):
        raise Refused(f"{name!r} has no key in secrets/identities.yaml")
    if derive(s) != pub:
        raise Refused(f"{name!r}: the SOPS key does not match pubkey_hex in identities.yml")
    return pub, s["nsec"]
