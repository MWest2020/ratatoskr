#!/usr/bin/env python3
"""Boomhuis chat agents — multi-agent listener around claude -p (sub first).

The agent DEFINITIONS (system prompt/chat facet, channels, npub) come from the
HANDBOOK (single source of truth): docs/agents/<name>.md, fetched over raw.
`agents.yml` only says WHICH agents this instance runs; private keys arrive
through env NSEC_<HANDLE> (from SOPS).

Guardrail: an agent is only run when (a) its definition can be loaded from the
handbook and (b) the npub in it matches the identity in identities.yml. No source
→ no spawn (fail-closed). The closed relay is the backstop at identity level.

Invariant: no shell, no repo write, no dispatch from here. Two markers do act:
`!sessie` starts a READ-ONLY work session (sessions.py) and `!route` forwards a
human's OWN words to another channel (routing.py) — neither hands an agent a
right it lacked; the listener acts, under conditions you can read.
"""
import os
import time

import agent_turn
import bootstrap
import relay
import room_flow
import rooms
import session_wiring
import sessions
import prompts
import notify
import reporting
import topology
import triggers

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RELAY = os.environ["BUZZ_RELAY_URL"]
POLL = int(os.environ.get("POLL_SECONDS", "5"))

CHANNELS = bootstrap.load_channels(ROOT)
NPUBS, PUB2NAME = bootstrap.load_identity_npubs(ROOT)
HUB = bootstrap.hub_handle(ROOT)   # role meta-agent; None = no hub spawned
ME_NAME = (os.environ.get("RATATOSKR_HUMAN")
           or os.environ.get("BOOMHUIS_HUMAN", "mark"))  # own messages do not push
CFG = bootstrap.load_yaml(os.path.join(HERE, "agents.yml"))
BASE = CFG["registry_base"]

# Active agent set: def from the handbook + nsec from env + npub match + model.
AGENTS = bootstrap.build_agents(CFG, BASE, NPUBS)
# Who answers in a channel when nobody is named. Checked here so a default that
# cannot speak fails at startup instead of silently at the first message.
DEFAULTS = bootstrap.load_channel_defaults(ROOT)
ROOMS = rooms.load(ROOT)   # shared rooms: channels with a `room:` block
bootstrap.check_channel_defaults(DEFAULTS, AGENTS)

AGENT_PUBS = set()  # filled with agent pubkeys (from identities, by name)


def name2pub_of(pub2name, handle):
    return next((p for p, h in pub2name.items() if h == handle), None)


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
    # Reader = the ORCHESTRATOR: owns every channel, so sees them all (measured
    # 2026-09-07: orchestrator 15/15, assistent 8/15, hub 4/15).
    read_nsec = os.environ.get("NSEC_ORCHESTRATOR", "").strip()
    if not read_nsec:
        raise SystemExit("[listener] NSEC_ORCHESTRATOR ontbreekt (zie agents/run.sh)")
    send = relay.sender(RELAY)
    fetch = lambda cid: relay.get_messages(cid, read_nsec, RELAY)  # noqa: E731
    run = relay.runner(read_nsec, RELAY)  # relay I/O for topology
    reg = sessions.Register(sessions.load(HERE))

    session_post, try_session = session_wiring.build(reg, AGENTS, send, HUB)
    run_turn = agent_turn.build(AGENTS, HUB, reg, send, CHANNELS, PUB2NAME, ROOT,
                                try_session)
    # In a room the listener speaks as the orchestrator (the channel owner), and
    # those lines are never input: otherwise a claim line would trigger a turn.
    orch_pub = name2pub_of(PUB2NAME, "orchestrator")
    room = room_flow.build(ROOMS, AGENTS, send, run_turn,
                           (read_nsec, NPUBS.get("orchestrator")), PUB2NAME)

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
                if cname in ROOMS and m.get("pubkey") == orch_pub:
                    continue
                content = m.get("content", "")
                # A human typing the marker: starter and requester are the same.
                try_session(content, writer, writer, cname, cid, mid)
                if cname in ROOMS:
                    room(cname, cid, msgs, i, content, writer, mid,
                         lambda h, c=content: prompts.mentioned(c, h))
                    continue
                # (a) @mentions of agents scoped here or relay members; (b) else: follow-up.
                targets, reason = triggers.pick(
                    content, msgs[:i], cname, AGENTS, PUB2NAME,
                    lambda h: scoped(h, cname, cid),
                    lambda h: prompts.mentioned(content, h),
                    DEFAULTS.get(cname))
                for handle in targets:
                    run_turn(handle, cname, cid, msgs, i, content, writer, mid, reason)
        reg.tick(session_post)  # progress/completion of running work sessions
        notify.flush()          # deliver what the push cooldown held back
        time.sleep(POLL)


if __name__ == "__main__":
    main()
