---
status: actief
last_reviewed: 2026-11-14
---

# Ping the owner from a working session

Mark talks to one coordinating session directly. Every other Claude session
reaches him through the relay, at a milestone or when blocked:

    IDENT=<your-ident> ~/ratatoskr/orchestrator/ping.sh '[<session>] message'

`ping.sh` reads the identity's nsec from SOPS, signs with buzz-cli and posts to
the self-hosted relay. No extra credentials on the agent host. Pinging from the
shared checkout is fine because it commits nothing; development work goes in
its own worktree (see the handbook's operating agreements).

## Identity rules

- **Never borrow an IDENT.** Identity = key pair = provenance. Posting under
  another session's key makes the audit trail untrue. `ping.sh` with an IDENT
  that is not in `identities.yml` fails with "unknown IDENT"; create one with
  `orchestrator/create-session-identity.py --name <name>`.
- `IDENT=bouwer` to #general works for sessions without their own key.
- **Membership is per channel.** A key that is a member of #general is not
  automatically a member of a project channel; the relay then answers
  "mentioned pubkeys are not channel members". `buzz channels members` needs
  its own `BUZZ_PRIVATE_KEY`.
- **The chat HTTP API signs everything as `mark`** (`POST /api/send` with the
  app token). To post as yourself, use `ping.sh`, not the API.
- Adding a member (`orchestrator/add-member.py`) is blocked for agents by the
  auto-mode classifier. Hand the owner the ready-to-run command.

## Start a build

A session starts a habitat build with the same line as Mark and odin, on the
**first** line of its ping (Mark, 2026-11-14: *"claude, odin, or jarvis mogen
dit."*):

    IDENT=claude CHAN=escalatie ~/ratatoskr/orchestrator/ping.sh \
      $'!build wordsworth some-change 123\nwhy: the change is merged, the issue is open'

- **Which IDENT.** A coding session uses `claude`; the voice bridge uses
  `jarvis`. Both are session identities (created 2026-11-14). The
  coordinating session that already pings as `odin` may keep doing so: odin is
  on the list too. What counts is the signing key, matched against
  `build_starters` in `agents/factory.yml`; an IDENT that is not on that list
  (`hubby`, `bouwer`, …) starts nothing, silently.
- **Which channel.** One where your identity and odin are both members: odin
  says `🔨 build started`, every verdict and every refusal in the channel the
  build came from. `claude` and `jarvis` are members of #escalatie. A session
  identity may not post in #general (`ping.sh` refuses it). For another
  channel, ask Mark to run `orchestrator/add-member.py --chan <channel> --name
  <ident>`.
- **First line only.** `!build` further down the message starts nothing.
- **No chat.** The listener acts on the marker and nothing else: a message
  from an agent identity is never answered as chat, with or without a marker.
  To ask odin something, go through Mark.
- **Same gates.** The repo list, the change on main, the slots, the daily
  budget (a session's build counts, like odin's), the circuit breaker and the
  issue check all apply; a refusal comes back as `⛔ build not started: …`.
  Sending the same refused line again within ten minutes gets no answer at all:
  fix the cause first. The issue names you as the starter. Details: [build from the
  chat](build-from-chat.md).

## The way back: Mark answers through odin

A ping reaches Mark's phone. His answer goes to odin in #general, for example
"tell the session: yes, add the rule". Odin then ends its answer with
`!session <id of Mark's message>`. The listener (`agents/session_inbox.py`)
checks two things:

- the marker comes from the hub;
- the message it points at is **Mark's own**, by pubkey, in that channel.

Only then does it append his words, unchanged, as one JSON line to
`~/.local/state/ratatoskr/session-inbox.jsonl` (mode 0600). Odin writes none of
the text, and an agent's message is never passed on.

The session watches that file with a background loop that ends when a line is
added, so it is notified when Mark answers:

    n=$(wc -l < ~/.local/state/ratatoskr/session-inbox.jsonl 2>/dev/null || echo 0)
    until [ "$(wc -l < ~/.local/state/ratatoskr/session-inbox.jsonl 2>/dev/null || echo 0)" -gt "$n" ]; do sleep 15; done
    tail -n 1 ~/.local/state/ratatoskr/session-inbox.jsonl
