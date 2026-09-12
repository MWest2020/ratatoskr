#!/usr/bin/env python3
"""Boomhuis chat agents — multi-agent listener around claude -p (sub first).

The agent DEFINITIONS (system prompt/chat facet, channels, npub) come from the
HANDBOOK (single source of truth): docs/agents/<name>.md, fetched over raw.
`agents.yml` only says WHICH agents this instance runs; private keys arrive
through env NSEC_<HANDLE> (from SOPS).

Guardrail: an agent is only run when (a) its definition can be loaded from the
handbook and (b) the npub in it matches the identity in identities.yml. No source
→ no spawn (fail-closed). The closed relay is the backstop at identity level.

Invariant: no shell, no repo write access, no dispatch from here. A `!sessie`
marker does start a READ-ONLY work session (see sessions.py) — that changes
nothing and delivers text in the channel.
"""
import os
import time

import bootstrap
import relay
import sessions
import prompts
import notify
import providers
import reporting
import topology

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))
MAX_CTX = 8


CHANNELS = bootstrap.load_channels(ROOT)
NPUBS, PUB2NAME = bootstrap.load_identity_npubs(ROOT)
HUB = bootstrap.hub_handle(ROOT)   # role meta-agent; None = no hub spawned
ME_NAME = (os.environ.get("RATATOSKR_HUMAN")
           or os.environ.get("BOOMHUIS_HUMAN", "mark"))  # own messages do not push
CFG = bootstrap.load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Active agent set: def from the handbook + nsec from env + npub match + model.
AGENTS = bootstrap.build_agents(CFG, BASE, NPUBS)

AGENT_PUBS = set()  # filled with agent pubkeys (from identities, by name)


def main():
    # Hold on to it as long as the listener lives: closing releases the lock.
    lock = bootstrap.only_me()            # noqa: F841 — the reference IS the point
    if lock is None:
        # Exit code 0, not an error: under systemd with `Restart=on-failure` a
        # non-zero exit would give a ten-second restart loop against a lock that
        # never frees. "One is already running" is the desired outcome.
        print("[listener] er draait al een listener op deze host — gestopt "
              "(twee listeners = elk bericht dubbel)", flush=True)
        return
    if not AGENTS:
        raise SystemExit("geen agents gespawnd (geen bron/nsec/npub-match)")
    # Reader = the ORCHESTRATOR: it owns every channel and so sees them all
    # (measured 2026-09-07: orchestrator 15/15, assistent 8/15, the hub 4/15).
    read_nsec = os.environ.get("NSEC_ORCHESTRATOR", "").strip()
    if not read_nsec:
        raise SystemExit("[listener] NSEC_ORCHESTRATOR ontbreekt (zie agents/run.sh)")
    send = relay.sender(RELAY)
    fetch = lambda cid: relay.get_messages(cid, read_nsec, RELAY)  # noqa: E731
    run = relay.runner(read_nsec, RELAY)  # relay I/O for topology
    reg = sessions.Register(sessions.load(HERE))

    def session_post(s, text):
        """Progress/result under the identity the TYPE declares."""
        c = AGENTS.get(s["identity"])
        if c:
            send(s["cid"], text, c["nsec"], c["npub"])

    def try_session(text, starter, requester, cname, cid, message_id=""):
        """Act on a `!sessie` marker. `starter` wrote the marker, `requester` is
        the person it is done for. Refusals are reported, not swallowed — a silent
        refusal looks like a session that found nothing."""
        mk = sessions.read_marker(text)
        if not mk:
            return
        type_name, task = mk
        s, reason = reg.start(type_name, task, starter, requester, cname, cid, message_id)
        if not s:
            print(f"[listener] sessie geweigerd ({starter}→{requester}/{type_name}): {reason}",
                  flush=True)
            c = AGENTS.get(HUB) or next(iter(AGENTS.values()))
            send(cid, f"⛔ no session: {reason}", c["nsec"], c["npub"])
            return
        on_behalf = "" if starter == requester else f" on behalf of @{requester}"
        print(f"[listener] sessie {type_name} gestart door {starter}{on_behalf} in #{cname}",
              flush=True)
        session_post(s, f"▶️ session `{type_name}` started by @{starter}{on_behalf} "
                        f"(max {s['max_s'] // 60} min) — "
                        f"task: {task[:120] or '(none)'}")

    reporting.report_missing_memberships(run, AGENTS, CHANNELS, PUB2NAME)
    name2pub = {h: p for p, h in PUB2NAME.items()}   # so we do not answer agents
    for h in AGENTS:
        AGENT_PUBS.add(name2pub.get(h))

    def scoped(h, cname, cid):  # mention scope: handbook OR relay member (pure)
        return topology.is_scoped(AGENTS[h]["channels"], cname, name2pub.get(h),
                                  lambda: topology.members(run, cid))  # lazy: only on need

    seen, seeded = set(), set()

    def seed(cid, msgs):
        # Mark the history of a (new) channel as seen. Only on a SUCCESSFUL read
        # (msgs≠None) — otherwise it gets 'seeded' plus history spam.
        for m in msgs:
            seen.add(m.get("id"))
        seeded.add(cid)

    for cid in topology.poll_channels(run, CHANNELS).values():
        msgs = fetch(cid)
        if msgs is not None:
            seed(cid, msgs)
    print(f"[listener] actief; agents uit handbook: {', '.join(AGENTS)}", flush=True)
    while True:
        for cname, cid in topology.poll_channels(run, CHANNELS).items():
            msgs = fetch(cid)
            if msgs is None:      # failed read → skip, try again next tick
                continue
            if cid not in seeded:  # channel just entered the poll set: mark the
                seed(cid, msgs)    # history as 'seen', do NOT answer old messages
                continue
            for i, m in enumerate(msgs):
                mid = m.get("id")
                if not mid or mid in seen:  # skip id-less messages (not dedupable)
                    continue
                seen.add(mid)
                # Notify before the agent filter: an agent ANSWER is exactly what
                # a human waits for. What does not notify is decided by
                # notify.should_notify.
                writer = PUB2NAME.get(m.get("pubkey"), "?")
                if notify.should_notify(cname, writer, m.get("content", ""), ME_NAME):
                    notify.push(cname, writer, m.get("content", ""))
                if m.get("pubkey") in AGENT_PUBS:
                    continue
                content = m.get("content", "")
                # A human typing the marker: starter and requester are the same.
                try_session(content, writer, writer, cname, cid, mid)
                # (a) @mentions of agents scoped here or relay members; (b) else: follow-up.
                targets = [h for h in AGENTS
                           if prompts.mentioned(content, h) and scoped(h, cname, cid)]
                reason = "mention"
                if not targets:
                    for prev in reversed(msgs[max(0, i - 10):i]):
                        if prev.get("pubkey") in AGENT_PUBS:
                            h = PUB2NAME.get(prev.get("pubkey"))
                            # a follow-up (without mention) stays def-channel-only
                            # (spec); membership only widens the mention branch above.
                            if h in AGENTS and cname in AGENTS[h]["channels"]:
                                targets = [h]
                                reason = "vervolg"
                            break  # only the most recent agent counts
                for handle in targets:
                    cfg = AGENTS[handle]
                    print(f"[listener] {reason} @{handle} in #{cname}: {content[:50]}", flush=True)
                    recent = msgs[max(0, i - MAX_CTX):i + 1]
                    p = prompts.build_prompt(handle, cname, recent, content, PUB2NAME)
                    know = prompts.channel_knowledge(ROOT, cname)
                    if know:
                        p = f"Kanaal-kennis (#{cname}):\n{know}\n\n" + p
                    if handle == HUB:
                        p = prompts.roster_text(AGENTS, HUB) + "\n\n" + p
                        lt = prompts.live_text(ROOT)
                        if lt:
                            p = lt + "\n\n" + p
                    try:
                        r = providers.run(cfg.get("provider"),
                                          cfg["system"] + prompts.LIMIT_CLAUSE
                                          + prompts.session_clause(reg.cfg, handle,
                                                                   writer), p,
                                          model=cfg.get("model"), allow=cfg.get("allow"),
                                          deny=cfg.get("deny"),
                                          progress=reporting.progress_poster(
                                              send, cid, cfg, handle))
                    except Exception as e:  # incl. timeout: the turn must never crash
                        r = {"answer": f"(fout: {e})", "error": str(e)[:120]}
                    ans = r.get("answer", "(geen antwoord)")
                    mk = sessions.read_marker(ans)
                    text = sessions.strip_marker(ans) if mk else ans
                    if text and send(cid, text, cfg["nsec"], cfg["npub"]):
                        print(f"[listener] {handle} antwoordde in #{cname} ({reason})", flush=True)
                    if mk:
                        # Odin wrote the marker, but the question came from `writer`.
                        try_session(ans, handle, writer, cname, cid, mid)
                    reporting.report_run(send, CHANNELS, handle, cname, cfg, r)
        reg.tick(session_post)  # progress/completion of running work sessions
        time.sleep(POLL)


if __name__ == "__main__":
    main()
