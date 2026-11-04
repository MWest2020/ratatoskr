## 1. Parse

- [ ] `agents/chain_next.py`: parse the `Next:` line (the only line followed) and a deploy precondition from a proposal's text; parse `Depends on` only as the list of parents for the eligibility check. Proof: `agents/test_chain_next.py` (named step, `Depends on` never returned as a step to queue, none named, precondition, malformed line).
- [ ] Read the proposal with the raw `Accept` header and tell "read failed" from "no next step named". Proof: `agents/test_chain_next_wiring.py` asserts the `gh api` call carries `Accept: application/vnd.github.raw+json`, that a base64/JSON body and a `gh` error give the "read failed" log and channel line, and that a proposal without `Next:` gives the distinct "no next step named" line.

## 2. Wire

- [ ] `build_wiring.follow_merges`: after a build's merge, read the proposal from main and queue the next step through the existing queue; say what was chained or why not. Proof: `agents/test_chain_next_wiring.py` drives merge and queue together (a seam, per AGENTS.md): merge of A queues B; no line queues nothing; a `gh` failure is said, not swallowed; B already queued is not doubled.
- [ ] Gates: a chained step respects the breaker, `max_concurrent` and `builds_per_day`. Proof: the same test file, one case per gate, and a mutation check that removing the gate call fails it.
- [ ] Eligibility: B is queued only when every parent in B's `Depends on` is merged, and a merged parent is never queued again. Proof: `agents/test_chain_next_wiring.py` (A merges with `Next: B`, B `Depends on: A`: B queued, A not; B with an unmerged second parent: nothing queued, reason said).
- [ ] Interplay with the wake: `propose_wiring.after_done` still tells odin to take the next step. Proof: `agents/test_chain_next_wiring.py` runs the merge (chain queues B), then odin's `!build B` through `try_build`, and asserts the refusal "already building or queued", that B has exactly one build, and that the circuit-breaker counter is unchanged.
- [ ] Deploy gap: the chain fires at the merge, not at deploy-done. Proof: `agents/test_chain_next_wiring.py` has a case where A is still deploying and B is queued anyway, and the how-to states the risk (see Docs).
- [ ] Build-only flag: a precondition step skips the `deploying` hand-off. Proof: `agents/test_chain_next_wiring.py` (no `deploying` entry, comment on the issue) and a control case that does deploy.
- [ ] Keep every changed `.py` within 200 lines (`scripts/line_limit.py`); put new logic in `chain_next.py`, not in `build_wiring.py`.

## 3. Docs

- [ ] `docs/how-to/build-from-chat.md`: new section "After the merge: the next step" (what is read: only `Next:`, with `Depends on` as eligibility; the gates; build-only for a deploy precondition; odin's duplicate `!build` is refused; the chain fires at the merge, so B may build on a main that is merged but not yet deployed; "read failed" versus "no next step named") and update `last_reviewed`. Proof: `scripts/docs_drift.py` passes.
- [ ] `agents/README.md`: mention `chain_next.py` if it lists modules (check with Grep first).

## 4. Check

- [ ] `bash scripts/verify.sh` is green and `openspec validate chain-next-step-after-merge --strict` passes.
