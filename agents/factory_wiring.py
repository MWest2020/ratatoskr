# SPDX-License-Identifier: MIT
"""Odin drives the factory; closing waits for Mark (odin-runs-the-factory, phase 4).

Mark, 2026-10-22: "odin can decide for new roles if need be, and new channels.
closing should be consulted with me."

Odin's markers, on the FIRST line of its answer only (a quote further down never
counts, as with !sessie and !build):

    !role                                  + a ```yaml block with the role spec
    !channel <name> <agent,agent> <purpose>
    !close role <name>   |   !close channel <name>

`!role` runs orchestrator/factory.py in the background; when it succeeds the
listener moves to main and restarts, so the new agent starts. `!channel` creates
the channel at once. `!close` only PROPOSES: nothing is closed until Mark answers
`!yes` (his own message, checked by pubkey through `writer`), and a proposal
expires after a day.
"""
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "orchestrator"))
import factory_ops  # noqa: E402

import bootstrap  # noqa: E402

ROLE = re.compile(r"^!role\s*$")
SPEC = re.compile(r"```ya?ml\s*\n(.*?)```", re.S)
CHANNEL = re.compile(r"^!channel\s+([a-z][a-z0-9_-]{1,30})\s+([a-z][a-z0-9,_-]{1,200})\s+(\S.{0,200})$")
CLOSE = re.compile(r"^!close\s+(role|channel)\s+([a-z][a-z0-9_-]{1,30})\s*$")
YES = re.compile(r"^\s*!yes\b", re.I)
PROPOSAL_TTL = 24 * 3600


def first_line(text):
    return ((text or "").strip().splitlines() or [""])[0].strip()


def setup(agents, hub, human, send, channels, runs_dir, base, popen=subprocess.Popen,
          run=subprocess.run, ops=factory_ops, now=time.time, log=print,
          fetch_def=bootstrap.fetch_def):
    voice = agents.get(hub) or {}
    jobs, pending = [], []
    os.makedirs(runs_dir, exist_ok=True)

    def say(cid, text):
        if voice:
            send(cid, text, voice["nsec"], voice["npub"])

    def start_role(text, cid):
        m = SPEC.search(text)
        if not m:
            return say(cid, "⛔ no role created: `!role` needs a ```yaml block with the spec")
        path = os.path.join(runs_dir, f"role-{int(now())}.yml")
        with open(path, "w") as fh:
            fh.write(m.group(1))
        out = path[:-4] + ".log"
        fh = open(out, "w")
        proc = popen(["uv", "run", "-q", os.path.join(ROOT, "orchestrator", "factory.py"),
                      "--spec", path], stdout=fh, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, cwd=ROOT, start_new_session=True)
        fh.close()   # the child holds its own descriptor
        jobs.append({"proc": proc, "out": out, "cid": cid})
        say(cid, "🏭 the factory is making the role; this takes a few minutes")

    def start_channel(m, cid):
        name, members, purpose = m.group(1), m.group(2).split(","), m.group(3)
        bad = [a for a in members if a not in agents]
        if bad or name in channels:
            return say(cid, f"⛔ no channel: {'unknown agents ' + str(bad) if bad else name + ' exists'}")
        p = run(["python3", os.path.join(ROOT, "orchestrator", "create-room.py"), "--name", name,
                 "--members", ",".join(members)], capture_output=True, text=True, timeout=120)
        ids = re.findall(r"#\S+ (?:created|exists already): ([0-9a-f-]{36})", p.stdout)
        if p.returncode != 0 or not ids:
            return say(cid, f"⛔ channel not created: {(p.stdout + p.stderr).strip()[-200:]}")
        try:
            ops.channel_record(name, ids[0], purpose)
        except ops.StepError as e:
            return say(cid, f"⚠ #{name} exists on the relay but not in channels.yml: {e}")
        say(cid, f"🆕 #{name} created with Mark, {', '.join(members)}; restarting to listen there")
        ops.redeploy_listener()

    def try_marker(text, starter, cname, cid):
        if starter != hub:
            return
        line = first_line(text)
        if ROLE.match(line):
            return start_role(text, cid)
        if m := CHANNEL.match(line):
            return start_channel(m, cid)
        if m := CLOSE.match(line):
            kind, name = m.group(1), m.group(2)
            known = name in (agents if kind == "role" else channels)
            if not known or (kind == "role" and name == hub):
                return say(cid, f"⛔ cannot propose closing {kind} {name!r}")
            pending[:] = [{"kind": kind, "name": name, "cid": cid, "at": now()}]
            say(cid, f"⏸ odin proposes to close {kind} **{name}**. Mark: answer `!yes` "
                     "here to confirm. Nothing happens until then (expires in 24 h).")

    def try_yes(content, writer, cid):
        if writer != human or not YES.match(content or ""):
            return
        live = [p for p in pending if p["cid"] == cid and now() - p["at"] < PROPOSAL_TTL]
        if not live:
            return say(cid, "nothing waits for a `!yes` here")
        p = live[-1]
        pending.remove(p)
        today = time.strftime("%Y-%m-%d", time.localtime(now()))
        try:
            if p["kind"] == "channel":
                ops.channel_close(p["name"], channels[p["name"]], os.environ.get(
                    "NSEC_ORCHESTRATOR", ""), today)
            else:
                ops.role_retire(p["name"], today)
        except ops.StepError as e:
            return say(cid, f"⛔ closing {p['kind']} {p['name']} failed: {e}")
        say(cid, f"✓ {p['kind']} {p['name']} closed on Mark's `!yes`; restarting")
        ops.redeploy_listener()

    def await_definition(j):
        """raw.githubusercontent caches ~5 minutes and its nodes disagree
        (2026-10-07): restart only after fetch_def serves the new definition
        three times in a row, or the listener would refuse the new agent."""
        if now() < j.get("next", 0):
            return
        j["next"] = now() + 30
        j["seen"] = j.get("seen", 0) + 1 if fetch_def(base, j["name"]) else 0
        if j["seen"] >= 3:
            jobs.remove(j)
            say(j["cid"], f"🔄 the handbook serves **{j['name']}**; restarting so it starts")
            ops.redeploy_listener()
        elif now() - j["made"] > 1200:
            jobs.remove(j)
            say(j["cid"], f"⚠ {j['name']} is made, but the handbook did not serve it within "
                          "20 minutes; it starts at the next restart")

    def tick():
        for j in list(jobs):
            if "name" in j:
                await_definition(j)
                continue
            if j["proc"].poll() is None:
                continue
            jobs.remove(j)
            with open(j["out"]) as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.startswith("{")]
            res = json.loads(lines[-1]) if lines else {"ok": False, "error": "no result"}
            if not res.get("ok"):
                why = res.get("error") or "; ".join(res.get("errors") or [])
                say(j["cid"], f"⛔ role not created: {why[:400]}")
                continue
            say(j["cid"], f"✅ role **{res['name']}** made ({'; '.join(res['done'])}). "
                          "It starts once the handbook serves it.")
            log(f"[listener] factory made {res['name']}", flush=True)
            jobs.append({"name": res["name"], "cid": j["cid"], "made": now()})

    return try_marker, try_yes, tick


def clause(handle, hub):
    """What the hub is told about the factory; other agents hear nothing."""
    if handle != hub:
        return ""
    return ("\n\nYou run the FACTORY. On the FIRST line of your answer:\n"
            "- `!role` followed by a ```yaml block: name, model (haiku|sonnet|opus), "
            "channels, skills (promoted skills only; a role's tools follow from them), "
            "mandate, contract (takes, produces, done_when, hands_off_to, not_mine), "
            "prompt. Creates a NEW role; existing roles are Mark's.\n"
            "- `!channel <name> <agent,agent> <purpose>` creates a channel with Mark "
            "and those agents.\n"
            "- `!close role <name>` or `!close channel <name>` only PROPOSES; Mark "
            "decides with `!yes`. Never close anything yourself.\n"
            "Create a role only when no existing agent's contract covers the work.")
