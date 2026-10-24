# SPDX-License-Identifier: MIT
"""Glue between the listener and the build road (build.py, build_runner.py).

`try_build` acts on a `!build` marker: the hub's own answer (first line only)
or Mark's own message. `tick` follows running chains. Every step leaves two
traces: a comment on the build's issue (the record) and a line in the channel
the build came from (so Mark sees it happen).
"""
import time

import activity
import branches
import build
import build_merge
import build_runner
import credits
import deploy
import issues as gh_issues


def setup(cfg, agents, hub, human, send, issues=gh_issues, log=print, builds=None,
          merger=build_merge, now=time.time, deployer=None, after_merge=None,
          after_fail=None, after_done=None):
    builds = builds or build_runner.Builds(cfg)
    merging = builds.merging   # PRs waiting for their checks (phase 2), persisted
    deploying = builds.deploying   # merges on their way to the homelab (phase 3)
    deployer = deployer or deploy.Deployer(cfg)
    voice = agents.get(hub) or {}

    def say(cid, text):
        if voice:
            send(cid, text, voice["nsec"], voice["npub"])

    def try_build(text, starter, cname, cid, own):
        mk = build.read_marker(text, own=own)
        if not mk:
            return
        if starter not in (hub, human):
            return say(cid, f"⛔ build not started: only {hub} or {human} start builds")
        repo, change, given = mk
        if any(b.get("change") == change for b in builds.running + builds.queued):
            return say(cid, f"ℹ `{change}` is already building or queued")
        name, why = build.check(cfg, repo, change, builds.running, capped=starter != human)
        if not name and any(q in why for q in build.QUEUEABLE):
            # 2026-10-24: a refused build was dropped and had to be asked for again
            builds.queued.append({"repo": repo, "change": change, "given": given,
                                  "cname": cname, "cid": cid, "starter": starter})
            builds.save()
            return say(cid, f"⏳ `{change}` queued: {why}; it starts when a chain finishes")
        if not name:
            log(f"[listener] build refused: {why}", flush=True)
            return say(cid, f"⛔ build not started: {why}")
        begin(name, change, given, cname, cid, starter)

    last_drain = [0.0]

    def drain_queue():
        """Start queued builds as they may; each waits on its own reason. Once a minute."""
        if now() - last_drain[0] < 60:
            return
        last_drain[0] = now()
        for q in list(builds.queued):
            name, why = build.check(cfg, q["repo"], q["change"], builds.running,
                                    capped=q["starter"] != human)
            if not name:
                continue            # still waiting, or e.g. the budget: it stays queued
            builds.queued.remove(q)
            builds.save()
            begin(name, q["change"], q["given"], q["cname"], q["cid"], q["starter"])

    def begin(name, change, given, cname, cid, starter):
        number = given
        if number and not build.open_issue(cfg["owner"], name, number):
            log(f"[listener] #{number} is not an open issue; opening a fresh one", flush=True)
            number = 0
        if not number:
            body = (f"Build of OpenSpec change `{change}`, started by **{starter}** from "
                    f"#{cname}. habitat chain: architect, builder, reviewer, security.")
            number, _, err = issues.create(name, f"build: {change}", body,
                                           ["agent-work", "build"])
            if err:
                return say(cid, f"⛔ build not started: could not open an issue on {name}: {err}")
        b = builds.start(name, change, number, cname, cid, starter)
        issues.comment(name, number, f"Build started by **{starter}** (image "
                       f"`{cfg['worker_image'].rsplit(':', 1)[-1][:12]}`). Run file: "
                       f"`{b['path']}`.")
        log(f"[listener] build started: {name} {change} #{number}", flush=True)
        tail = f" (#{given} was not an open issue)" if given and given != number else ""
        say(cid, f"🔨 build started: `{change}` on {name} · {name}#{number}{tail}")

    def on_event(b, kind, role, detail):
        text = build_runner.comment(kind, role, detail)
        if kind in ("passed", "failed"):
            rep = build_runner.report(detail.get("store"))
            billed = credits.repo_billed(b["repo"])
            if billed:
                credits.record("build-role", rep.get("total_cost_usd"),
                               f"{b['repo']}:{b['change']}:{role}")
            activity.record("habitat", role, b["repo"], model=detail.get("model") or "default",
                            cost=rep.get("total_cost_usd"), turns=rep.get("num_turns"),
                            billing="api" if billed else "subscription",
                            ref=f"{b['change']}:{rep.get('verdict', kind)}")
        err = issues.comment(b["repo"], b["issue"], text)
        tail = f" · {b['repo']}#{b['issue']}"
        mark = {"passed": "✅", "failed": "❌", "done": "🏁"}[kind]
        say(b["cid"], f"{mark} {text.splitlines()[0]}{tail}"
                      + (f" (⚠ not on the issue: {err})" if err else ""))
        b.setdefault("verdicts", []).append(text.splitlines()[0])
        if kind in ("done", "failed"):
            branches.tidy(cfg["owner"], b, keep=(detail["branch"],) if kind == "done" else (),
                          log=log, keep_builder=kind == "failed")
        if kind == "done":
            open_pr(b, detail["branch"])
        elif kind == "failed" and after_fail:
            after_fail(b, text)   # the hub decides: retry, or tell Mark

    def open_pr(b, branch):
        """The chain passed every role: a PR, merged later once CI agrees."""
        pr, err = merger.open_pr(cfg["owner"], b["repo"], branch, b["change"], b["issue"],
                                 b.get("verdicts", []))
        tail = f" · {b['repo']}#{b['issue']}"
        if err:
            issues.comment(b["repo"], b["issue"], f"Could not open the PR: {err}")
            return say(b["cid"], f"⚠ no PR for `{b['change']}`: {err}{tail}")
        issues.comment(b["repo"], b["issue"], f"PR #{pr} opened from `{branch}`; it is "
                       "merged once every check passes.")
        say(b["cid"], f"🔀 PR #{pr} opened; merging when CI passes{tail}")
        merging.append({k: v for k, v in b.items() if k != "proc"} | {"pr": pr, "next": 0})
        builds.save()

    def follow_merges():
        """At most once a minute per PR: merge, wait, or stop."""
        for m in list(merging):
            if now() < m["next"]:
                continue
            m["next"] = now() + 60
            verdict, detail = merger.checks(cfg["owner"], m["repo"], m["pr"])
            if verdict == "wait":
                continue
            merging.remove(m)
            builds.save()
            tail = f" · {m['repo']}#{m['issue']}"
            if verdict == "stop":
                why = getattr(merger, "failure_excerpt", lambda *a: "")(cfg["owner"], m["repo"],
                                                                      m["pr"])
                issues.comment(m["repo"], m["issue"], f"Not merged: {detail}."
                               + (f"\n\n{why}" if why else ""))
                say(m["cid"], f"⛔ PR #{m['pr']} not merged: {detail}{tail}")
                if after_fail and m.get("kind") != "archive" and m.get("change"):
                    after_fail(m, f"CI stopped the merge of PR #{m['pr']}: {detail}."
                               + (f"\n\n{why}" if why else ""))
                continue
            err = merger.merge(cfg["owner"], m["repo"], m["pr"])
            issues.comment(m["repo"], m["issue"], f"Merged PR #{m['pr']} ({detail})."
                           if not err else f"Merge of PR #{m['pr']} failed: {err}")
            say(m["cid"], (f"✅ merged PR #{m['pr']} ({detail})" if not err
                           else f"⛔ merge of PR #{m['pr']} failed: {err}") + tail)
            if not err and after_merge:
                after_merge(m)
            if not err and m.get("kind") not in ("propose", "archive") and not deployer.recipe(m["repo"]) \
                    and after_done:
                after_done(m)            # no deploy for this repo: archive right away
            if not err and m.get("kind") not in ("propose", "archive") and deployer.recipe(m["repo"]):
                sha, why = merger.merged_sha(cfg["owner"], m["repo"], m["pr"])
                if sha:
                    deploying.append({k: m.get(k) for k in ("repo", "issue", "cid", "change")}
                                     | {"sha": sha, "phase": "image", "started": now()})
                    builds.save()
                else:
                    issues.comment(m["repo"], m["issue"], f"Not deployed: {why}.")

    def follow_deploys():
        """One step per deploy per tick; every step on the issue and in the room."""
        for d in list(deploying):
            state, msg = deployer.step(d)
            if state == "wait" and not msg:
                continue
            tail = f" · {d['repo']}#{d['issue']}"
            if state in ("done", "fail"):
                deploying.remove(d)
            if state == "done" and after_done:
                after_done(d)            # deployed: archive the change
            builds.save()
            mark = {"next": "🚚", "done": "🚀", "fail": "⛔", "wait": "⏳"}[state]
            text = {"done": f"Deployed to the homelab: {msg}.", "fail": f"Deploy stopped: {msg}."}
            issues.comment(d["repo"], d["issue"], text.get(state, f"Deploy: {msg}."))
            say(d["cid"], f"{mark} deploy {d['repo']}: {msg}{tail}")

    def tick():
        builds.tick(on_event)
        drain_queue()
        follow_merges()
        follow_deploys()

    tick.builds = builds   # the propose road queues its PRs on the same follower
    return try_build, tick


def builds_of(tick):
    return tick.builds
