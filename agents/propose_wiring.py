# SPDX-License-Identifier: MIT
"""Glue for the propose road (agents/propose.py) in the listener.

`try_propose` acts on the hub's `!propose` (first line). `tick` follows the
writing sessions: when one ends, the listener checks the result, opens the PR
and hands it to the build road's merge follower (build_wiring), marked
`kind: propose` so that it is not deployed: an OpenSpec change is Markdown.
When that PR merges, `after_merge` gives the hub one follow-up turn, so the
change it decided gets built without anyone nudging it.
"""
import os
import time

import build
import issues as gh_issues
import propose

CLONES = os.path.expanduser("~")


def setup(cfg, agents, hub, send, pub2name, builds, fetch, run_turn, issues=gh_issues,
          now=time.time, log=print, start=propose.start, check=propose.check,
          publish=propose.publish, archive=propose.archive, refused=propose.refused_writes):
    voice = agents.get(hub) or {}
    jobs = builds.proposing   # persisted in state.json, adopted after a restart

    def say(cid, text):
        if voice:
            send(cid, text, voice["nsec"], voice["npub"])

    def try_propose(answer, starter, cname, cid, msgs, requester):
        mk = propose.read_marker(answer) if starter == hub else None
        if not mk:
            return
        repo, change, summary = mk
        name = build.canonical_repo(cfg, repo)
        if not name:
            return say(cid, f"⛔ no proposal: `{repo}` is not on the factory's list")
        n, _, err = issues.create(name, f"propose: {change}", f"**{hub}** in #{cname}: {summary}\n\n"
                                  "A propose session writes the OpenSpec change; the PR "
                                  "merges once CI passes, then the change is built.",
                                  ["agent-work", "propose"])
        if err:
            return say(cid, f"⛔ no proposal: could not open an issue on {name}: {err}")
        job, why = start(os.path.join(CLONES, name), change, summary, msgs, pub2name, requester)
        if not job:
            issues.comment(name, n, f"Not started: {why}.")
            return say(cid, f"⛔ no proposal for `{change}`: {why} · {name}#{n}")
        jobs.append({**job, "repo": name, "issue": n, "cid": cid, "cname": cname,
                     "msgs": msgs[-14:], "requester": requester,
                     "started": now(), "pid": getattr(job["proc"], "pid", None)})
        builds.save()
        log(f"[listener] propose session {name} {change} #{n}", flush=True)
        say(cid, f"📝 writing the change `{change}` on {name} · {name}#{n}")

    def finish(j):
        tail = f" · {j['repo']}#{j['issue']}"
        why = check(j)
        denied = refused(j) if why else []
        if denied and not j.get("retried"):
            again, err = start(os.path.join(CLONES, j["repo"]), j["change"], j["summary"],
                               j.get("msgs") or [], pub2name, j.get("requester", hub))
            if again:
                issues.comment(j["repo"], j["issue"], f"{len(denied)} writes inside the fence "
                               "were refused (debug log in `~/.local/state/ratatoskr/propose-debug/`); "
                               "retrying the session once.")
                jobs.append({**j, **again, "retried": True, "started": now(),
                             "pid": getattr(again["proc"], "pid", None)})
                return builds.save()
        if denied:
            why += (f"; {len(denied)} writes inside the fence were refused "
                    "(see ~/.local/state/ratatoskr/propose-debug/)")
        if why:
            issues.comment(j["repo"], j["issue"], f"No PR: {why}.")
            return say(j["cid"], f"⛔ change `{j['change']}` not proposed: {why}{tail}")
        pr, err = publish(j, j["repo"], cfg["owner"])
        if err:
            issues.comment(j["repo"], j["issue"], f"No PR: {err}.")
            return say(j["cid"], f"⛔ change `{j['change']}` written but no PR: {err}{tail}")
        issues.comment(j["repo"], j["issue"], f"PR #{pr} opened; merged once every check "
                       "passes, then the change is built.")
        say(j["cid"], f"🔀 change `{j['change']}` proposed in PR #{pr}{tail}")
        builds.merging.append({"repo": j["repo"], "change": j["change"], "issue": j["issue"],
                               "cid": j["cid"], "cname": j["cname"], "pr": pr, "next": 0,
                               "kind": "propose"})
        builds.save()

    def tick():
        for j in list(jobs):
            if j["proc"].poll() is None:
                if now() - j["started"] > propose.MAX_S:
                    if hasattr(j["proc"], "kill"):
                        j["proc"].kill()
                    jobs.remove(j)
                    builds.save()
                    say(j["cid"], f"⏹ the propose session for `{j['change']}` ran out of time")
                continue
            jobs.remove(j)
            builds.save()
            finish(j)

    def after_merge(m):
        """A merged proposal wakes the hub to build it."""
        if m.get("kind") != "propose":
            return
        msgs = fetch(m["cid"]) or []
        run_turn(hub, m.get("cname", ""), m["cid"], msgs, max(len(msgs) - 1, 0),
                 f"The OpenSpec change `{m['change']}` is on {m['repo']} main (PR #{m['pr']}, "
                 f"issue {m['repo']}#{m['issue']}). If it is the decided one, build it now: "
                 f"`!build {m['repo']} {m['change']} {m['issue']}` on the first line.",
                 "", "", "propose-merged", followup=True)

    def after_fail(b, text):
        """A failed build wakes the hub too: retry or tell Mark (the daily build
        budget caps retries)."""
        msgs = fetch(b["cid"]) or []
        run_turn(hub, b.get("cname", ""), b["cid"], msgs, max(len(msgs) - 1, 0),
                 f"The build of `{b['change']}` on {b['repo']} failed: {text} "
                 f"(issue {b['repo']}#{b['issue']}). Decide: start it again with `!build` "
                 "if the cause is gone; amend the change with `!propose` (same id) when "
                 "the cause belongs in it, then build; or tell Mark what blocks it.",
                 "", "", "build-failed", followup=True)

    def after_done(entry):
        """A change that is merged (and deployed where a recipe says so) gets
        archived by the same road: PR, CI, merge; no deploy, no wake."""
        if entry.get("kind") in ("propose", "archive") or not entry.get("change"):
            return
        pr, err = archive(os.path.join(CLONES, entry["repo"]), entry["repo"], cfg["owner"],
                          entry["change"])
        tail = f" · {entry['repo']}#{entry['issue']}"
        if err:
            issues.comment(entry["repo"], entry["issue"], f"Not archived: {err}.")
            return say(entry["cid"], f"⚠ `{entry['change']}` not archived: {err}{tail}")
        builds.merging.append({"repo": entry["repo"], "change": entry["change"],
                               "issue": entry["issue"], "cid": entry["cid"], "pr": pr,
                               "next": 0, "kind": "archive"})
        builds.save()
        say(entry["cid"], f"🗄 archiving `{entry['change']}` in PR #{pr}{tail}")

    return try_propose, tick, after_merge, after_fail, after_done
