# SPDX-License-Identifier: MIT
"""The factory's side effects, one function per place a role has to exist.

Each step is idempotent where it can be, so a role that stopped halfway can be
finished by running the factory again with the same spec. Every command is a
fixed argv; nothing from the spec reaches a shell.
"""
import os
import subprocess
import time

import yaml

HANDBOOK = os.path.expanduser("~/handbook")
RATATOSKR = os.path.expanduser("~/ratatoskr")
WORK = os.path.expanduser("~/.worktrees")
RELAY = "ws://192.168.178.60:3000"
BUZZ = os.path.expanduser("~/.local/bin/buzz")
ID = ["-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com"]
SOPS_ENV = dict(os.environ, SOPS_AGE_KEY_FILE=os.path.expanduser("~/.config/sops/age/keys.txt"))


class StepError(Exception):
    pass


def run(argv, cwd=None, env=None, inp=None, timeout=300, ok=(0,)):
    p = subprocess.run(argv, cwd=cwd, env=env, input=inp, capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode not in ok:
        raise StepError(f"{' '.join(argv[:4])}: {(p.stderr or p.stdout).strip()[-300:]}")
    return p.stdout


def fresh_worktree(repo, name, bare_repo=False):
    """A clean detached worktree of origin/main, recreated every run."""
    path = os.path.join(WORK, name)
    run(["git", "-C", repo, "fetch", "-q", "origin"])
    if os.path.isdir(path):
        run(["git", "-C", repo, "worktree", "remove", "--force", path])
    run(["git", "-C", repo, "worktree", "add", "-q", "--detach", path, "origin/main"])
    if bare_repo:   # ~/ratatoskr has core.bare=true; the worktree needs its own false
        gitdir = open(os.path.join(path, ".git")).read().split("gitdir:")[1].strip()
        with open(os.path.join(gitdir, "config.worktree"), "w") as fh:
            fh.write("[core]\n\tbare = false\n")
    return path


def handbook_pr(name, text):
    """Write the definition, run the gate, open the PR, merge it once every check
    passes. A new role is odin's to create (Mark, 2026-10-22)."""
    wt = fresh_worktree(HANDBOOK, f"hb-factory-{name}")
    path = os.path.join(wt, "docs", "agents", f"{name}.md")
    if os.path.exists(path):
        raise StepError(f"docs/agents/{name}.md already exists — changing a role is Mark's")
    with open(path, "w") as fh:
        fh.write(text)
    run(["uv", "run", "-q", "python", "scripts/check_agent_tools.py"], cwd=wt)
    branch = f"factory/{name}"
    run(["git", "checkout", "-q", "-b", branch], cwd=wt)
    run(["git", "add", f"docs/agents/{name}.md"], cwd=wt)
    run(["git", *ID, "commit", "-q", "-m", f"agents: {name}, created by the factory on odin's "
         "decision\n\nratatoskr change odin-runs-the-factory, phase 4."], cwd=wt)
    run(["git", "push", "-q", "-u", "origin", branch], cwd=wt)
    url = run(["gh", "pr", "create", "--repo=MWest2020/handbook", f"--head={branch}",
               "--base=main", f"--title=agents: {name} (factory)",
               "--body=Created by the factory on odin's decision. Closing or changing it is "
               "Mark's."], cwd=wt).strip()
    pr = url.rsplit("/", 1)[-1]
    for _ in range(60):
        out = run(["gh", "pr", "checks", pr, "--repo=MWest2020/handbook",
                   "--json=name,bucket", "--jq=.[].bucket"], ok=(0, 8, 1))
        buckets = out.split()
        if buckets and all(b in ("pass", "skipping") for b in buckets) and "pass" in buckets:
            run(["gh", "pr", "merge", pr, "--repo=MWest2020/handbook", "--merge"])
            return url
        if any(b in ("fail", "cancel") for b in buckets):
            raise StepError(f"handbook PR {url} has a failing check; not merged")
        time.sleep(15)
    raise StepError(f"handbook PR {url}: checks did not finish in 15 minutes")


def ratatoskr_identity(name, pub, npub, priv, nsec, today):
    """identities.yml, the SOPS key, the run list; one commit on ratatoskr main."""
    wt = fresh_worktree(RATATOSKR, f"rt-factory-{name}", bare_repo=True)
    idp = os.path.join(wt, "identities.yml")
    doc = yaml.safe_load(open(idp))
    if name in doc["identities"]:
        raise StepError(f"identity {name!r} already exists")
    head = open(idp).read().split("identities:")[0]
    doc["identities"][name] = {"rol": "chat-agent", "status": "actief", "pubkey_hex": pub,
                               "npub": npub, "aangemaakt": today}
    with open(idp, "w") as fh:
        fh.write(head + yaml.safe_dump(doc, default_flow_style=False, sort_keys=False,
                                       allow_unicode=True))
    secp = os.path.join(wt, "secrets", "identities.yaml")
    sd = yaml.safe_load(run(["sops", "-d", secp], cwd=wt, env=SOPS_ENV))
    sd["identities"][name] = {"privkey_hex": priv, "nsec": nsec}
    plain = yaml.safe_dump(sd, default_flow_style=False, sort_keys=False)
    enc = run(["sops", "-e", "--input-type=yaml", "--output-type=yaml",
               "--filename-override", secp, "/dev/stdin"], cwd=wt, env=SOPS_ENV, inp=plain)
    with open(secp, "w") as fh:
        fh.write(enc)
    ap = os.path.join(wt, "agents", "agents.yml")
    text = open(ap).read()
    if f"  - {name}\n" not in text:
        with open(ap, "w") as fh:
            fh.write(text.rstrip("\n") + f"\n  - {name}\n")
    run(["git", "add", "identities.yml", "secrets/identities.yaml", "agents/agents.yml"], cwd=wt)
    run(["git", *ID, "commit", "-q", "-m", f"identity: {name}, created by the factory"], cwd=wt)
    run(["git", "push", "-q", "origin", "HEAD:main"], cwd=wt, timeout=600)


def relay_membership(name, pub, nsec, channels, orchestrator_nsec, about):
    """Relay member, bot in each channel (signed by the orchestrator, which owns
    them), and the agent's own profile name."""
    run(["ssh", "-o", "BatchMode=yes", "buzz-relay", "sudo", "-n", "docker", "exec",
         "buzz-prod-relay-1", "buzz-admin", "add-member", "--pubkey", pub, "--role", "member"])
    time.sleep(2)
    env = dict(os.environ, BUZZ_PRIVATE_KEY=orchestrator_nsec, BUZZ_RELAY_URL=RELAY)
    for cid in channels:
        run([BUZZ, "channels", "add-member", "--channel", cid, "--pubkey", pub, "--role", "bot"],
            env=env, ok=(0, 1))
    run([BUZZ, "users", "set-profile", "--name", name, "--about", about[:120]],
        env=dict(os.environ, BUZZ_PRIVATE_KEY=nsec, BUZZ_RELAY_URL=RELAY))

