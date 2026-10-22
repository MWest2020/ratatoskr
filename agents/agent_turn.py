# SPDX-License-Identifier: MIT
"""One agent turn: build the prompt, run the model, act on its markers, post.

Pulled out of listener.py's poll loop so that a second caller can start a turn:
the shared room (room_flow.py), where a hand-off gives the next agent a turn
without a new human message. The loop body was the only place this existed,
and a hand-off cannot be written as "another iteration of the loop".
"""
import build
import factory_wiring
import prompts
import providers
import readshell
import reporting
import routing
import session_inbox
import sessions

MAX_CTX = 8


def build_turn(agents, hub, reg, send, channels, pub2name, root, try_session, log=print,
               human="mark", try_build=None, factory=None, try_factory=None):
    """`run_turn(...) -> (answer, posted)`, closed over the listener's state."""

    def run_turn(handle, cname, cid, msgs, i, content, writer, mid, reason,
                 extra="", suffix="", clean=None):
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
        try:
            r = providers.run(cfg.get("provider"),
                              cfg["system"] + prompts.LIMIT_CLAUSE
                              + prompts.session_clause(reg.cfg, handle, writer)
                              + prompts.route_clause(cfg)
                              + readshell.clause(cfg)
                              + session_inbox.clause(handle, hub)
                              + build.clause(handle, hub, factory or {})
                              + factory_wiring.clause(handle, hub), p,
                              model=cfg.get("model"), allow=cfg.get("allow"),
                              deny=cfg.get("deny"),
                              progress=reporting.progress_poster(send, cid, cfg, handle))
        except Exception as e:  # incl. timeout: the turn must never crash
            r = {"answer": f"(fout: {e})", "error": str(e)[:120]}
        ans = r.get("answer", "(geen antwoord)")
        ans = routing.handle(ans, handle, cfg, cname, msgs, pub2name, channels, send, cid)
        ans = session_inbox.handle(ans, handle, hub, cname, msgs, pub2name, human)
        mk = sessions.read_own_marker(ans)
        text = sessions.strip_own_marker(ans) if mk else ans
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
        if mk:
            # The agent wrote the marker, but the question came from `writer`.
            try_session(ans, handle, writer, cname, cid, mid, own=True)
        reporting.report_run(send, channels, handle, cname, cfg, r)
        return ans, posted

    return run_turn
