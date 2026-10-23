# SPDX-License-Identifier: MIT
"""The factory's operations after a role exists: channels, closing, redeploy.

Creating a channel is odin's; closing a channel or retiring a role happens
only on Mark's `!yes` (openspec change odin-runs-the-factory). Split from
factory_steps.py to keep both under 200 lines.
"""
import json
import os
import re
import subprocess

import yaml

from factory_steps import BUZZ, ID, RATATOSKR, RELAY, StepError, fresh_worktree, run


def _ratatoskr_commit(tag, edit, message):
    """Edit files in a fresh ratatoskr worktree and push one commit to main."""
    wt = fresh_worktree(RATATOSKR, f"rt-factory-{tag}", bare_repo=True)
    paths = edit(wt)
    if not paths:
        return
    run(["git", "add", *paths], cwd=wt)
    run(["git", *ID, "commit", "-q", "-m", message], cwd=wt)
    run(["git", "push", "-q", "origin", "HEAD:main"], cwd=wt, timeout=600)


def channel_record(name, cid, purpose):
    """A new channel in channels.yml, so the listener polls it by name."""
    def edit(wt):
        p = os.path.join(wt, "channels.yml")
        text = open(p).read()
        if f"\n  {name}:\n" in text:
            raise StepError(f"channel {name!r} is already in channels.yml")
        with open(p, "w") as fh:
            fh.write(text.rstrip("\n") + f"\n  {name}:\n    id: {cid}\n"
                     f"    doel: {json_str(purpose)}   # created by the factory on odin's decision\n")
        return ["channels.yml"]
    _ratatoskr_commit(f"ch-{name}", edit, f"channels: #{name}, created by the factory")


def channel_close(name, cid, orchestrator_nsec, today):
    """Archive on the relay and mark it archived in channels.yml (Mark's !yes)."""
    env = dict(os.environ, BUZZ_PRIVATE_KEY=orchestrator_nsec, BUZZ_RELAY_URL=RELAY)
    run([BUZZ, "channels", "archive", "--channel", cid], env=env)

    def edit(wt):
        p = os.path.join(wt, "channels.yml")
        text = open(p).read()
        head = f"\n  {name}:\n    id: {cid}\n"
        if head not in text:
            raise StepError(f"channel {name!r} with id {cid} not in channels.yml")
        with open(p, "w") as fh:
            fh.write(text.replace(head, head + f"    archived: {today}   # Mark's !yes\n", 1))
        return ["channels.yml"]
    _ratatoskr_commit(f"close-{name}", edit, f"channels: archive #{name} (Mark's !yes)")


def role_retire(name, today):
    """Off the run list and the identity inactive (Mark's !yes). The handbook
    definition stays as history; the listener no longer starts the agent."""
    def edit(wt):
        ap = os.path.join(wt, "agents", "agents.yml")
        lines = open(ap).read().splitlines(keepends=True)
        with open(ap, "w") as fh:
            fh.write("".join(ln for ln in lines if ln.strip() != f"- {name}"))
        idp = os.path.join(wt, "identities.yml")
        text = open(idp).read()
        doc = yaml.safe_load(text)
        if name not in doc["identities"]:
            raise StepError(f"identity {name!r} not found")
        doc["identities"][name]["status"] = "inactief"
        doc["identities"][name]["gestopt"] = today
        with open(idp, "w") as fh:
            fh.write(text.split("identities:")[0] + yaml.safe_dump(
                doc, default_flow_style=False, sort_keys=False, allow_unicode=True))
        return ["agents/agents.yml", "identities.yml"]
    _ratatoskr_commit(f"retire-{name}", edit, f"agents: retire {name} (Mark's !yes)")

def json_str(s):
    return json.dumps(" ".join(str(s).split())[:200], ensure_ascii=False)


def redeploy_listener(tree=os.path.expanduser("~/ratatoskr-listener")):
    """Move the listener tree to main and restart it; the new process reads the
    new run list, channels and definitions."""
    run(["git", "-C", tree, "fetch", "-q", "origin"])
    run(["git", "-C", tree, "checkout", "-q", "--detach", "origin/main"])
    subprocess.Popen(["systemctl", "--user", "restart", "ratatoskr-agents"],
                     start_new_session=True)



def with_room_member(text, name, channels):
    """channels.yml text with `name` added to the room members of each channel
    in `channels` that is a shared room; unchanged when none is a room. Pure."""
    doc = yaml.safe_load(text)
    for c in channels:
        if not (doc["channels"].get(c) or {}).get("room"):
            continue
        m = re.search(rf"(\n  {re.escape(c)}:\n(?:    .*\n)*?      members: \[)([^\]]*)\]", text)
        if not m:
            raise StepError(f"#{c}: no `members: [...]` line in its room block")
        if name not in [x.strip() for x in m.group(2).split(",")]:
            text = text[:m.end(2)] + f", {name}" + text[m.end(2):]
    return text


def room_members_add(name, channels):
    """A new role in a shared room joins that room's triage; otherwise it only
    ever answers an @mention (2026-10-23, pilotleider in #werkplaats)."""
    def edit(wt):
        p = os.path.join(wt, "channels.yml")
        old = open(p).read()
        new = with_room_member(old, name, channels)
        if new == old:
            return []
        with open(p, "w") as fh:
            fh.write(new)
        return ["channels.yml"]
    _ratatoskr_commit(f"room-{name}", edit, f"channels: {name} joins the room(s) {channels}")
