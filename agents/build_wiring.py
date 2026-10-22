# SPDX-License-Identifier: MIT
"""Glue between the listener and the build road (build.py, build_runner.py).

`try_build` acts on a `!build` marker: the hub's own answer (first line only)
or Mark's own message. `tick` follows running chains. Every step leaves two
traces: a comment on the build's issue (the record) and a line in the channel
the build came from (so Mark sees it happen).
"""
import time

import build
import build_merge
import build_runner
import issues as gh_issues


def setup(cfg, agents, hub, human, send, issues=gh_issues, log=print, builds=None,
          merger=build_merge, now=time.time):
    builds = builds or build_runner.Builds(cfg)
    merging = builds.merging   # PRs waiting for their checks (phase 2), persisted
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
        repo, change, number = mk
        name, why = build.check(cfg, repo, change, builds.running)
        if not name:
            log(f"[listener] build refused: {why}", flush=True)
            return say(cid, f"⛔ build not started: {why}")
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
        say(cid, f"🔨 build started: `{change}` on {name} · {name}#{number}")

    def on_event(b, kind, role, detail):
        text = build_runner.comment(kind, role, detail)
        err = issues.comment(b["repo"], b["issue"], text)
        tail = f" · {b['repo']}#{b['issue']}"
        mark = {"passed": "✅", "failed": "❌", "done": "🏁"}[kind]
        say(b["cid"], f"{mark} {text.splitlines()[0]}{tail}"
                      + (f" (⚠ not on the issue: {err})" if err else ""))
        b.setdefault("verdicts", []).append(text.splitlines()[0])
        if kind == "done":
            open_pr(b, detail["branch"])

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
                issues.comment(m["repo"], m["issue"], f"Not merged: {detail}.")
                say(m["cid"], f"⛔ PR #{m['pr']} not merged: {detail}{tail}")
                continue
            err = merger.merge(cfg["owner"], m["repo"], m["pr"])
            issues.comment(m["repo"], m["issue"], f"Merged PR #{m['pr']} ({detail})."
                           if not err else f"Merge of PR #{m['pr']} failed: {err}")
            say(m["cid"], (f"✅ merged PR #{m['pr']} ({detail})" if not err
                           else f"⛔ merge of PR #{m['pr']} failed: {err}") + tail)

    def tick():
        builds.tick(on_event)
        follow_merges()

    return try_build, tick
