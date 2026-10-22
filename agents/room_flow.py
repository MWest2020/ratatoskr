# SPDX-License-Identifier: MIT
"""A human message in a shared room: who takes it, which issue it is, and the
turns and hand-offs that follow. Everything an agent says lands on the issue.

The order (openspec change shared-room):
1. **mention**: an @member takes it; it continues the room's current issue, or
   opens one;
2. **follow-up**: no mention, a member spoke recently and the room has a
   current issue, so that member continues it;
3. **triage**: otherwise the contracts decide, and a new issue is opened.

Fail-closed on the trail: without an issue no turn starts, because an
untracked turn is exactly what Mark asked the issues to prevent. A comment that
fails later is said in the room instead of being lost.
"""
import issues as gh_issues
import rooms
import triage


def build(rooms_cfg, agents, send, run_turn, voice, pub2name,
          issues=gh_issues, triage_run=triage.run):
    """`handle(cname, cid, msgs, i, content, writer, mid, mentioned)`."""

    def say(cid, text):
        send(cid, text, voice[0], voice[1])

    def handle(cname, cid, msgs, i, content, writer, mid, mentioned):
        room = rooms_cfg[cname]
        members = [h for h in room["members"] if h in agents]
        earlier = msgs[:i]
        cur = rooms.current_issue(content, earlier, room["repos"])
        named = [h for h in members if mentioned(h)]
        last = rooms.last_agent(earlier, members, pub2name)
        title, why = content.strip().splitlines()[0][:80] if content.strip() else "", ""
        if named:
            owners, reason = named, "mention"
        elif cur and last:
            owners, reason = [last], "vervolg"
        else:
            t, err = triage_run(content, room, agents)
            if not t:
                say(cid, f"⚠ nobody took this: {err}. Name an agent with @ to go on.")
                return
            owners, reason, why = t["owners"], "triage", t["reason"]
            title = t["title"] or title
            cur = rooms.find_ref(content, room["repos"]) or (t["repo"], 0)
        repo, n = cur if cur else (room["repos"][0], 0)
        if n == 0:
            body = (f"**{writer}** in #{cname}:\n\n{content}\n\n---\n"
                    f"Taken by {', '.join(owners)} ({reason}). {why}")
            n, _, err = issues.create(repo, title or "room work", body,
                                      issues.labels(cname, owners[0]))
            if err:
                say(cid, f"⚠ not started: could not open an issue on {repo}: {err}")
                return
        else:
            err = issues.comment(repo, n, f"**{writer}** in #{cname}:\n\n{content}")
            if err:
                say(cid, f"⚠ not recorded on {rooms.ref(repo, n)}: {err}")
        if reason != "vervolg":
            say(cid, f"→ {' and '.join(owners)} {'takes' if len(owners) == 1 else 'take'} "
                     f"this ({reason}{': ' + why if why else ''})" + rooms.suffix(repo, n))
        for owner in owners:
            chain(owner, room, members, cname, cid, msgs, i, content, writer, mid,
                  reason, repo, n)

    def chain(owner, room, members, cname, cid, msgs, i, content, writer, mid,
              reason, repo, n):
        """One turn, then follow its hand-offs up to the room's hop limit."""
        tail = rooms.suffix(repo, n)
        for hop in range(room["max_hops"] + 1):
            cfg = agents[owner]
            extra = rooms.clause(cname, room, owner, cfg.get("contract"), repo, n,
                                 issues.url(repo, n))
            ans, posted = run_turn(owner, cname, cid, msgs, i, content, writer, mid,
                                   reason, extra=extra, suffix=tail, clean=rooms.clean)
            if posted:
                err = issues.comment(repo, n, f"**{owner}**:\n\n{posted}")
                if err:
                    say(cid, f"⚠ {owner}'s answer is not on the issue: {err}" + tail)
            finished = rooms.done(ans)
            if finished:
                err = issues.close(repo, n, f"Done ({owner}): {finished}")
                say(cid, f"✓ {owner}: {finished}"
                         + (f" (⚠ could not close the issue: {err})" if err else "") + tail)
                return
            h = rooms.handoff(ans)
            if not h:
                return
            target, line = h
            if target not in rooms.handoff_targets(cfg.get("contract"), members, owner):
                say(cid, f"⚠ {owner} tried to hand off to {target}; its contract "
                         "does not name that agent under 'Hands off to'." + tail)
                return
            if hop == room["max_hops"]:
                say(cid, f"⚠ hand-off limit ({room['max_hops']}) reached: "
                         f"{owner} wanted to pass this to {target}. Over to you, Mark." + tail)
                return
            issues.relabel(repo, n, f"agent:{owner}", f"agent:{target}")
            issues.comment(repo, n, f"Handed from {owner} to {target}: {line}")
            say(cid, f"↪ {owner} → {target}: {line}" + tail)
            content = f"{owner} hands this to you: {line}\n\nTheir answer:\n{posted}"
            owner, reason = target, "handoff"

    return handle
