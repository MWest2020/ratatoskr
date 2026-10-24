# SPDX-License-Identifier: MIT
"""One agent turn: build the prompt, run the model, act on its markers, post.

Pulled out of listener.py's poll loop so that a second caller can start a turn:
the shared room (room_flow.py), where a hand-off gives the next agent a turn
without a new human message. The loop body was the only place this existed,
and a hand-off cannot be written as "another iteration of the loop".
"""
import re

import activity
import agent_skills
import build
import consult
import credits
import repo_read
import propose
import factory_wiring
import prompts
import providers
import readshell
import reporting
import routing
import session_inbox
import sessions

MAX_CTX = 8


# Markers count on an answer's FIRST line only (a quote further down must never
# act). On 2026-10-23 the prompt told agents the LAST line, odin obeyed, and its
# `!sessie` was dropped without a word while it told Mark a session had started.
MARKER = re.compile(r"^!(sessie|build|role|channel|close|consult|propose)\b", re.M)


def misplaced(answer):
    """A visible note when an answer has a marker that is NOT on its first line."""
    body = (answer or "").strip().split("\n", 1)
    hits = MARKER.findall(body[1]) if len(body) > 1 else []
    if not hits:
        return ""
    return (f"\n\n⚠ `!{hits[0]}` was not on the first line of this answer, so nothing "
            "was started. A marker only counts on the first line.")


def build_turn(agents, hub, reg, send, channels, pub2name, root, try_session, log=print,
               human="mark", try_build=None, factory=None, try_factory=None,
               may_speak=lambda handle, cname, cid: True, try_propose=None):
    """`run_turn(...) -> (answer, posted)`, closed over the listener's state."""

    def run_turn(handle, cname, cid, msgs, i, content, writer, mid, reason,
                 extra="", suffix="", clean=None, followup=False):
        """`extra` goes in front of the prompt (room context), `suffix` after the
        posted answer (the issue reference), `clean` takes the room's markers
        out of what is posted. Returns the answer as the model wrote it (the
        caller reads its markers) and what was posted without the suffix, ""
        when nothing was posted."""
        cfg = agents[handle]
        log(f"[listener] {reason} @{handle} in #{cname}: {content[:50]}", flush=True)
        recent = msgs[max(0, i - MAX_CTX):i + 1]
        kan_routeren = bool(routing.allowed_channels(cfg))
        p = prompts.build_prompt(handle, cname, recent, content, pub2name,
                                 met_ids=kan_routeren)
        know = prompts.channel_knowledge(root, cname)
        if know:
            p = f"Kanaal-kennis (#{cname}):\n{know}\n\n" + p
        if handle == hub:
            p = prompts.roster_text(agents, hub) + "\n\n" + p
            lt = prompts.live_text(root)
            if lt:
                p = lt + "\n\n" + p
        if extra:
            p = extra + "\n\n" + p
        billed = credits.channel_billed(cname)   # this channel runs on the API credits
        if billed and credits.refusal():
            send(cid, f"⛔ {credits.refusal()}; not answering until it is raised or a "
                      "new month starts", cfg["nsec"], cfg["npub"])
            return "", ""
        try:
            r = providers.run(cfg.get("provider"),
                              cfg["system"] + prompts.LIMIT_CLAUSE
                              + prompts.session_clause(reg.cfg, handle, writer)
                              + prompts.route_clause(cfg)
                              + readshell.clause(cfg)
                              + session_inbox.clause(handle, hub)
                              + build.clause(handle, hub, factory or {})
                              + factory_wiring.clause(handle, hub)
                              + consult.clause(handle, hub)
                              + (prompts.KEEP_GOING if handle == hub else "")
                              + repo_read.clause(factory or {})
                              + propose.clause(handle, hub)
                              + agent_skills.clause(cfg.get("skills")), p,
                              model=cfg.get("model"),
                              allow=(cfg.get("allow") or []) + agent_skills.allow_rules(cfg.get("skills")),
                              deny=cfg.get("deny"),
                              progress=reporting.progress_poster(send, cid, cfg, handle),
                              env=credits.env(providers.agent_env()) if billed else None)
        except Exception as e:  # incl. timeout: the turn must never crash
            r = {"answer": f"(fout: {e})", "error": str(e)[:120]}
        if billed:
            credits.record("turn", r.get("cost"), f"{handle}#{cname}")
        activity.record("chat", handle, cname, model=r.get("model"), skills=cfg.get("skills"),
                        skills_used=r.get("skills_used"), tools=r.get("tools"),
                        cost=r.get("cost"), turns=r.get("turns"),
                        billing="api" if billed else "subscription", ref=reason)
        ans = r.get("answer", "(geen antwoord)")
        ans = routing.handle(ans, handle, cfg, cname, msgs, pub2name, channels, send, cid)
        ans = session_inbox.handle(ans, handle, hub, cname, msgs, pub2name, human)
        mk = sessions.read_own_marker(ans)
        text = sessions.strip_own_marker(ans) if mk else ans
        text += misplaced(ans)
        ck = consult.read_marker(ans) if handle == hub else None
        if ck:
            text = consult.strip_marker(text)
            if followup:      # the follow-up to a consult ends the exchange
                text += "\n\n⚠ no consult from a follow-up turn"
                ck = None
        if try_propose and handle == hub and propose.read_marker(ans):
            try_propose(ans, handle, cname, cid, msgs, writer)
            text = propose.strip_markers(text)
        elif handle == hub:
            text += propose.unread(ans)
        if try_factory and handle == hub:
            try_factory(ans, handle, cname, cid)
        if try_build and build.read_marker(ans):
            try_build(ans, handle, cname, cid, own=True)
            text = build.strip_marker(text)
        posted = ""
        if clean:
            text = clean(text)
        if text and send(cid, text + suffix, cfg["nsec"], cfg["npub"]):
            log(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
            posted = text
        if mk and followup:
            # A follow-up to a finished session may not start the next one.
            send(cid, "⚠ no new session from a follow-up turn", cfg["nsec"], cfg["npub"])
            mk = None
        if mk:
            # The agent wrote the marker, but the question came from `writer`.
            try_session(ans, handle, writer, cname, cid, mid, own=True)
        reporting.report_run(send, channels, handle, cname, cfg, r)
        if ck:
            # Only the hub's own answer is read for !consult, and the consulted
            # turns below are not: no chains (consult.py).
            take, refused = consult.plan(ck[0], hub, agents,
                                         lambda h: may_speak(h, cname, cid))
            if refused:
                send(cid, "⚠ not consulted: " + "; ".join(refused), cfg["nsec"], cfg["npub"])
            answers = []
            for name in take:
                _, said = run_turn(name, cname, cid, msgs, i,
                                   consult.prompt_for(ck[1], content, hub), writer, mid, "consult")
                if said:
                    answers.append(f"**{name}:** {said}")
            if answers:
                run_turn(hub, cname, cid, msgs, i, consult.followup_for(answers, content),
                         writer, mid, "consult-done", followup=True)
        return ans, posted

    return run_turn
