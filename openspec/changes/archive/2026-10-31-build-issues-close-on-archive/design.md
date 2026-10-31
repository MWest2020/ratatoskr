## Decisions

- **Scope is the change id.** An issue is matched by its exact title, `build: <change>` or `propose: <change>`, as `issues.open_titled` already does for `propose:`. No fuzzy matching: a wrong close is worse than a missed one, and a missed one still shows in the digest.
- **Detection is stateless; the state is main itself.** On a 30-minute tick, for each open `build:`/`propose:` issue, the listener reads `openspec/changes` and `openspec/changes/archive` on the issue's repository, one `gh api` call each. It closes only if the change id is absent from `changes` AND exactly one archive directory `YYYY-MM-DD-<id>` exists. This covers the chain's own archive and out-of-chain archives (by hand) alike, and is restart-safe because nothing is stored.
- **Removal without archive is never closed, only logged.** The change is gone and no archive directory exists (a split, a removal): the listener logs that and leaves the issue for a human. Zero or more than one archive match is treated the same way.
- **One closer.** The existing close of `propose:` issues after a chain's own archive PR (`agents/propose_wiring.py`, `after_merge`) is folded into this closer, not a second mechanism. The comment names the archive path.
- **Load and rate limits.** Only repositories that have an open build issue are polled, at most one pair of calls per repository per tick. On a `gh` error or rate limit the tick is skipped for that repository and the reason is logged. A missed close is acceptable; a wrong close is not.
- **The dated archive id is not carried** through `propose_git.archive` or `state.json`. The closer always resolves it from the archive listing, so old `merging` entries work without a fallback.
- **Close only open issues.** Already-closed issues are not listed, so the closer is idempotent and a restart does not comment twice. The comment goes in before the close.
- **A failed close says why.** A `gh` failure is logged with its reason, not swallowed (AGENTS.md: silent failure is the fault).

## Rejected alternatives

- **Keep closing by hand from the coding session.** That is what happened for #305, #80 and #104; the point is that the factory tidies up without a human.
- **Extend only the existing `propose:` close to `build:`.** Fixes the chain's own archive but not hand-archives, which are exactly the cases seen.
- **Snapshot of `openspec/changes/` per tick, closing on a diff.** Needs stored state, misses changes archived while the listener was down, and cannot tell removal from archive without the archive listing anyway.
- **Watching merged PRs.** Misses direct pushes to main and needs the PR-to-change mapping.
- **Carrying the dated archive id through `propose_git.archive` and `state.json`.** Only covers the chain's own archives and leaves old `merging` entries needing a fallback.
- **Closing removed changes with the superseding PR as pointer.** Cannot be told apart from a mistaken deletion; see the proposal's open questions.
