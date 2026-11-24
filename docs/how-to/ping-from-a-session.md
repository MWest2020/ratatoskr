---
status: actief
last_reviewed: 2026-11-24
---

# Ping the owner from a working session

Mark talks to one coordinating session directly. Every other Claude session
reaches him through the relay, at a milestone or when blocked:

    IDENT=<your-ident> CHAN=<channel> ~/ratatoskr/orchestrator/ping.sh '[<session>] message'

## The coding session is heimdall

The coding session on agent-lxc (the desk Jarvis hands work to; it decides and
builds) pings as **`heimdall`**, display name *Heimdall* (Mark, 2026-11-24:
"ok, Heimdall is goed"):

    IDENT=heimdall CHAN=escalatie ~/ratatoskr/orchestrator/ping.sh 'message'

Until 2026-11-24 it pinged as `odin`. That was confusing: `@odin` is also the
chat agent, the hub that answers Mark in #general, and a ping signed with odin's
key cannot be told apart from odin's own answer. `odin` is the chat agent only
from now on; a session no longer borrows its key.

heimdall is a session identity (`rol: sessie`), so it follows the session rules
below. Its channels are #escalatie, where it pings Mark and starts builds, and
#statistics, for test pings (odin is a bot there). It becomes a member only
when Mark has run the relay phase below; until then the relay refuses its
posts. It is **not** in #general: that is the hub channel, where Mark talks to
odin alone (spec `identity-registry`, "one hub agent in the human channel"),
and `ping.sh` refuses a session there. Mark's answer still comes back through
odin and the session inbox (below).

heimdall's `!build` counts only after a listener restart: the listener reads
`identities.yml` and `build_starters` once, at startup.

`ping.sh` reads the identity's nsec from SOPS, signs with buzz-cli and posts to
the self-hosted relay. No extra credentials on the agent host. Pinging from the
shared checkout is fine because it commits nothing; development work goes in
its own worktree (see the handbook's operating agreements).

## Identity rules

- **Never borrow an IDENT.** Identity = key pair = provenance. Posting under
  another session's key makes the audit trail untrue. `ping.sh` with an IDENT
  that is not in `identities.yml` fails with "unknown IDENT".
- **A new session identity** is made in two phases. First a session, in a
  worktree, on a branch (`--phase registry` is the default):

      uv run orchestrator/create-session-identity.py --name <name> \
        --display <Name> --about '<one line: what it is>' [--chan <channel> ...]

  This writes the key pair, the key into `secrets/identities.yaml` (SOPS,
  fail-closed) and the entry into `identities.yml`; commit both in a PR. A
  session identity's key and build rights are part of that session's mandate,
  so **Mark merges this PR himself.** Then the relay phase: **Mark runs it; the
  orchestrator key signs** the channel changes, never Mark's key:

      uv run orchestrator/create-session-identity.py --name <name> [--chan <channel> ...] \
        --phase relay --owner-step

  #escalatie is always included; #general and archived channels are refused.
  The relay phase refuses anything that is not an active `sessie` identity, a
  name outside `^[a-z][a-z0-9-]{1,30}$`, and a `pubkey_hex` that is not 64
  hex characters or does not match the key in SOPS (it ends up in an ssh
  command). Those checks stop mistakes; they are **not the gate**. The gate is
  the permission layer and Mark choosing to run the step: `--owner-step` only
  says that this is his step.
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

    IDENT=heimdall CHAN=escalatie ~/ratatoskr/orchestrator/ping.sh \
      $'!build wordsworth some-change 123\nwhy: the change is merged, the issue is open'

- **Which IDENT.** The coding session on agent-lxc uses `heimdall` (since
  2026-11-24); another coding session uses `claude`; the voice bridge uses
  `jarvis`. All three are session identities. `odin` is on the list as the
  chat agent, not for a session to borrow. What counts is the signing key, matched against
  `build_starters` in `agents/factory.yml`; an IDENT that is not on that list
  (`hubby`, `bouwer`, …) starts nothing, silently.
- **Which channel.** One where your identity and odin are both members: odin
  says `🔨 build started`, every verdict and every refusal in the channel the
  build came from. `claude` and `jarvis` are members of #escalatie; `heimdall` is once Mark has
  run its relay phase. A session
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
  After a lasting refusal (repository not on the list, or the circuit breaker),
  the same line again within ten minutes gets no answer at all. A missing change
  on main is answered every time, so merge the spec and send it again. The issue names you as the starter. Details: [build from the
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
