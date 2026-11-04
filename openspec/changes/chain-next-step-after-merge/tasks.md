## 1. Parse

- [ ] `agents/chain_next.py`: parse `Next:` / `Depends on` lines and a deploy precondition from a proposal's text. Proof: `agents/test_chain_next.py` (named step, `Depends on`, none named, precondition, malformed line).

## 2. Wire

- [ ] `build_wiring.follow_merges`: after a build's merge, read the proposal from main and queue the next step through the existing queue; say what was chained or why not. Proof: `agents/test_chain_next_wiring.py` drives merge and queue together (a seam, per AGENTS.md): merge of A queues B; no line queues nothing; a `gh` failure is said, not swallowed; B already queued is not doubled.
- [ ] Gates: a chained step respects the breaker, `max_concurrent` and `builds_per_day`. Proof: the same test file, one case per gate, and a mutation check that removing the gate call fails it.
- [ ] Build-only flag: a precondition step skips the `deploying` hand-off. Proof: `agents/test_chain_next_wiring.py` (no `deploying` entry, comment on the issue) and a control case that does deploy.
- [ ] Keep every changed `.py` within 200 lines (`scripts/line_limit.py`); put new logic in `chain_next.py`, not in `build_wiring.py`.

## 3. Docs

- [ ] `docs/how-to/build-from-chat.md`: new section "After the merge: the next step" (what is read, the gates, build-only for a deploy precondition) and update `last_reviewed`. Proof: `scripts/docs_drift.py` passes.
- [ ] `agents/README.md`: mention `chain_next.py` if it lists modules (check with Grep first).

## 4. Check

- [ ] `bash scripts/verify.sh` is green and `openspec validate chain-next-step-after-merge --strict` passes.
