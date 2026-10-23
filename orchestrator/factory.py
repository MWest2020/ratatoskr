# /// script
# dependencies = ["coincurve>=20", "bech32>=1.2", "pyyaml>=6"]
# ///
# SPDX-License-Identifier: MIT
"""The agent factory: a role spec becomes a running chat agent.

Replaces create-agent.py (stale paths, no model/tools/skills, signed as Mark).
Openspec change odin-runs-the-factory, phase 4. Odin decides new roles (Mark,
2026-10-22); closing one, or changing an existing one, stays Mark's.

    uv run orchestrator/factory.py --spec role.yml [--dry-run]

Order, so a failure leaves the least behind: validate and render (pure), then
the handbook definition (PR, gate, merge), then the identity in ratatoskr, then
relay and channel membership. The listener picks the agent up on its next
restart, once it can fetch the merged definition.
"""
import argparse
import datetime
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import factory_def  # noqa: E402
import factory_ops  # noqa: E402
import factory_steps as steps  # noqa: E402


def keypair():
    from bech32 import bech32_encode, convertbits
    from coincurve import PrivateKey
    pk = PrivateKey(os.urandom(32))
    pub = pk.public_key.format(compressed=True)[1:].hex()
    enc = lambda hrp, hexs: bech32_encode(hrp, convertbits(bytes.fromhex(hexs), 8, 5))  # noqa: E731
    return pub, enc("npub", pub), pk.to_hex(), enc("nsec", pk.to_hex())


def context():
    """Register, channels and existing roles, read from the sources of truth."""
    hb = steps.fresh_worktree(steps.HANDBOOK, "hb-factory-read")
    reg = {e["slug"]: e.get("tools") or [] for e in
           yaml.safe_load(open(os.path.join(hb, "inventory", "skills-register.yml")))["skills"]}
    existing = {f[:-3] for f in os.listdir(os.path.join(hb, "docs", "agents")) if f.endswith(".md")}
    chans = {n: c["id"] for n, c in
             yaml.safe_load(open(os.path.join(ROOT, "channels.yml")))["channels"].items()
             if not c.get("archived")}
    return reg, chans, existing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--dry-run", action="store_true", help="validate and render only")
    a = ap.parse_args(argv)
    spec = yaml.safe_load(open(a.spec)) or {}
    reg, chans, existing = context()
    errs = factory_def.validate(spec, reg, set(chans), existing)
    if errs:
        print(json.dumps({"ok": False, "errors": errs}))
        return 2
    today = datetime.date.today().isoformat()
    name = spec["name"]
    if a.dry_run:
        print(factory_def.render(spec, "npub1dryrun", reg, today))
        return 0
    pub, npub, priv, nsec = keypair()
    done = []
    try:
        url = steps.handbook_pr(name, factory_def.render(spec, npub, reg, today))
        done.append(f"handbook {url}")
        steps.ratatoskr_identity(name, pub, npub, priv, nsec, today)
        done.append("identity in ratatoskr")
        sd = yaml.safe_load(steps.run(["sops", "-d", os.path.join(ROOT, "secrets", "identities.yaml")],
                                      cwd=ROOT, env=steps.SOPS_ENV))
        steps.relay_membership(name, pub, nsec, [chans[c] for c in spec["channels"]],
                               sd["identities"]["orchestrator"]["nsec"], spec["mandate"])
        done.append("relay and channels")
        factory_ops.room_members_add(name, spec["channels"])
        done.append("room triage")
    except (steps.StepError, OSError) as e:
        print(json.dumps({"ok": False, "name": name, "done": done, "error": str(e)}))
        return 1
    print(json.dumps({"ok": True, "name": name, "npub": npub, "done": done}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
