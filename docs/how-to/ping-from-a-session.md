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
