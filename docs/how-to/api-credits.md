---
status: current
last_reviewed: 2026-10-24
---

# Work on the API credits

Mark has $100 of Anthropic API credits a month that only API-key use draws
on. The game (MWest2020/convergence) runs on them; everything else stays on
the subscription. Its assignment: *"Stop at a cost overrun and report it,
instead of going on."* And Mark, on the pace: *"fail fast, burn fast. quick
results, but solid ones ... Nitro!"* (2026-10-24).

## What is billed

| work | billed when | how |
|---|---|---|
| chat turns | the channel has `billing: api` in `channels.yml` (`#convergence`) | `ANTHROPIC_API_KEY` in that turn's environment only |
| propose sessions | the repository is in `factory.yml` `api_repos` | the same, for that session |
| habitat chains | the repository is in `api_repos` | `HABITAT_AUTH=api`: the worker gets the key instead of the subscription token |

The key is `secrets/anthropic-api.yaml` (SOPS), decrypted once at listener
start (`agents/credits.py`) and held in memory. `providers.agent_env()` passes
no keys, so unbilled work never sees it.

## The budget

- Every billed cost is a line in `~/.local/state/ratatoskr/api-ledger.jsonl`:
  each chat turn, each propose session, each habitat role (from its run
  report).
- `api_budget_usd` (95 a month) is the limit. Billed work starts only while
  the month has room: a chat turn needs any room, a proposal $3, a chain its
  worst case (four roles at `api_max_budget_usd`). When that does not fit,
  the build is refused. When it fits but not alongside the worst case of every
  billed chain already running, the build is **queued** and starts once those
  finish and their real cost is known (2026-10-24: $58 of $95 left, a third
  chain was refused and dropped).
- Billed chains run side by side, at most `max_concurrent_api` (3), and do
  not count against the subscription's `builds_per_day`; money guards them.
  Subscription chains keep their own limit of one at a time.
- A billed build that finds every slot taken is **queued**, not dropped: it
  is kept in `state.json` (`queued`) and starts on the first tick a slot is
  free, oldest first. A build of a change already running or queued is said
  so and not started twice. (2026-10-24: with three chains running, pitch was
  refused and had to be asked for again.)

The Console's own spend limit on the key's workspace is the hard stop behind
this one.
