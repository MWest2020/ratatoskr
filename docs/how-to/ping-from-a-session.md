---
status: actief
last_reviewed: 2026-09-23
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
