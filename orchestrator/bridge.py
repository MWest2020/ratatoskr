#!/usr/bin/env python3
"""Boomhuis → habitat bridge (add-habitat-bridge, part B) — Mark is the gate.

Gatekeeper model: NOTHING dispatches autonomously. Only an explicit confirmation
message from MARK in #bouw of the form

    !dispatch <role> <change> <repo>

sets anything in motion. The orchestrator then takes the last `bouwer` plan from
the thread as task/context, commits it as a task file in the target repo (git),
and runs `dispatch.sh` with `HABITAT_TASK_REF` — BUT only when BRIDGE_LIVE=1.
Without that flag the bridge posts the exact dispatch command back so Mark runs
it himself, supervised. That keeps the cage fire human-gated.

Env:
  BUZZ_PRIVATE_KEY   orchestrator nsec (from SOPS)
  BUZZ_RELAY_URL     ws://192.168.178.60:3000
  BRIDGE_LIVE        1 = really run dispatch.sh; otherwise only prepare and show
  DISPATCH_SH        path to habitat dispatch/dispatch.sh (host with kubectl)
  WORKER_IMAGE       pinned worker image SHA (for dispatch.sh)
"""
import json
import os
import re
import subprocess
import time

BUZZ = os.environ.get("BUZZ_BIN", "buzz")
RELAY = os.environ["BUZZ_RELAY_URL"]
LIVE = os.environ.get("BRIDGE_LIVE") == "1"
DISPATCH_SH = os.environ.get("DISPATCH_SH", "")
BOUW = "69cf0949-f1ab-4383-9627-8ef0f51977e1"
MARK = "821de7df04297a3a5e53c1ae423456b32826505a1caef5fe0979a4940720c2db"
BOUWER = "2827e3d844551b81f4193fd7e64b60141759a5a4848482f48b9ad2c2fd938b74"
ORCH_NPUB = "npub1yucg7falmtraq5wkc7wt4nlu7g8ve322hn9hf9wmdzjc7fwss0cq5gl3hs"
POLL = int(os.environ.get("POLL_SECONDS", "5"))
CMD = re.compile(r"^!dispatch\s+(\S+)\s+(\S+)\s+(\S+)", re.M)


def env():
    e = dict(os.environ)
    e["BUZZ_RELAY_URL"] = RELAY
    return e


def get(cid):
    p = subprocess.run([BUZZ, "messages", "get", "--channel", cid],
                       env=env(), capture_output=True, text=True, timeout=25)
    try:
        d = json.loads(p.stdout)
    except Exception:
        return []
    m = d if isinstance(d, list) else d.get("messages", [])
    return sorted(m, key=lambda x: x.get("created_at", 0))


def post(cid, content):
    subprocess.run([BUZZ, "messages", "send", "--channel", cid, "--content", "-",
                    "--mention", ORCH_NPUB], env=env(), input=content,
                   capture_output=True, text=True, timeout=25)


def last_bouwer_plan(msgs, before_ts):
    for m in reversed(msgs):
        if m.get("created_at", 0) < before_ts and m.get("pubkey") == BOUWER:
            return m.get("content", "")
    return ""


def handle(msgs, m):
    """Handle a confirmed !dispatch from Mark. The gate has already been passed
    (sender == mark). Prepares the dispatch; only fires when BRIDGE_LIVE is set."""
    mm = CMD.search(m.get("content", ""))
    if not mm:
        return
    role, change, repo = mm.group(1), mm.group(2), mm.group(3)
    plan = last_bouwer_plan(msgs, m.get("created_at", 0))
    if not plan:
        post(BOUW, f"⚠️ geen bouwer-plan gevonden vóór je !dispatch — vraag @bouwer eerst een change-voorstel.")
        return
    # task/context is committed by the orchestrator in the TARGET REPO (git);
    # here we only show the path contract. The real git write + dispatch.sh runs
    # only supervised (BRIDGE_LIVE), or Mark runs it himself.
    task_ref = f".habitat/task-{change}.md"
    cmd = (f"HABITAT_TASK_REF={task_ref} {DISPATCH_SH or '<dispatch.sh>'} "
           f"{role} {change} {repo}")
    if LIVE and DISPATCH_SH:
        post(BOUW, f"🚀 dispatch (live) — rol={role} change={change} repo={repo}\n"
                   f"taak-ref: {task_ref}")
        # (The real git write of the plan to the target repo + the dispatch.sh
        #  call belong here; deliberately gated until the first supervised run.)
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        post(BOUW, f"dispatch-resultaat (exit {r.returncode}):\n{(r.stdout or r.stderr)[-500:]}")
    else:
        post(BOUW, f"✅ klaar om te dispatchen (poortwachter gepasseerd). Draai dit "
                   f"op de kubectl-host, met het bouwer-plan in {task_ref} van "
                   f"{repo}:\n\n    {cmd}\n\n(Zet BRIDGE_LIVE=1 om dit automatisch "
                   f"te laten draaien zodra je de brug vertrouwt.)")


def main():
    seen = set()
    for m in get(BOUW):
        seen.add(m.get("id"))
    print(f"[bridge] actief; poortwachter=mark, live={LIVE}", flush=True)
    while True:
        msgs = get(BOUW)
        for m in msgs:
            if m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            # GATE: only Mark's explicit !dispatch counts
            if m.get("pubkey") == MARK and CMD.search(m.get("content", "")):
                print(f"[bridge] !dispatch van mark: {m.get('content','')[:60]}", flush=True)
                handle(msgs, m)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
