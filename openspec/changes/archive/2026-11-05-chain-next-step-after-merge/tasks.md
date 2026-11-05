## 1. Parse (`agents/chain_next.py`, new, pure)

- [x] `parse(text)` per the grammar in design.md: `next` (first backticked id under `## Next`), `parents` (every backticked id under `## Depends on`), `precondition` (a `## Deploy precondition` section exists), `malformed` (a `## Next` section without a backticked id). Proof: `agents/test_chain_next.py`: a named step; heading case and spacing variants; prose around ids ignored; two parents; only the first section of a name counts; no `## Next`; a `## Next` without an id is malformed; a precondition; an id inside a fenced code block under another heading is not a parent.

## 2. Read and decide (`agents/chain_wiring.py`, new)

- [x] `read_proposal(owner, repo, change, runner)` uses `gh api` with `-H "Accept: application/vnd.github.raw+json"` and returns `(text, "")` or `("", reason)`; a body starting with `{` is a failed read. Proof: `agents/test_chain_wiring.py` asserts the header in the `gh` call, a `gh` error and a JSON body both give "read failed".
- [x] `merged(owner, repo, parent, just_merged, runner)`: true for the just-merged change; otherwise a merged PR whose title is exactly `build: <parent>`. Proof: tests for both, a near-miss title (`build: <parent>-x`) is not merged, and a test that the title `build_merge.open_pr` writes matches this search.
- [x] `setup(cfg, hub, say, try_build, runner=subprocess.run, log=print)` returns `chain(m)` with the outcomes "read failed", "no next step named", "malformed `## Next`", "next step archived" (loop guard), "parent not merged" (names it), "deploy precondition, a person starts it", and "requested". Only "requested" calls `try_build(f"!build {repo} {next}", hub, cname, cid, own=True)`. Each outcome is said in `m["cid"]`, or logged when the entry has no `cid`. Proof: one test per outcome, each asserting whether `try_build` was called.

## 3. Wire (seam)

- [x] `propose_wiring.setup(..., try_build=None)` builds `chain` when `try_build` is given; `after_merge` calls `chain(m)` for a build (`kind` neither `propose` nor `archive`). `listener.py` passes `try_build=try_build` on its existing `propose_wiring.setup(...)` call without adding a line. `build_wiring.py` and `build.py` are not changed. Proof: `agents/test_chain_seam.py` drives `build_wiring.setup` + `propose_wiring.setup` together with fakes for `gh`, merge and habitat: merge of A with `## Next` B queues B through `try_build`; with `max_concurrent` reached B waits in `builds.queued`; with the breaker tripped for B the refusal is said; a second request (odin's `!build B`) is refused as "already building or queued", B has one build and the breaker count is unchanged.
- [x] Line budget: `python3 scripts/line_limit.py` stays green; check after each edit, not at the end.

## 4. Docs

- [x] `docs/how-to/build-from-chat.md`: section "After the merge: the next step": the `## Next` / `## Depends on` / `## Deploy precondition` grammar with an example; the "merged" rule; the gates; that a precondition step is not chained (a person starts it); the deploy gap; the loop guard; odin's duplicate `!build` being refused. Update `last_reviewed`. Proof: `scripts/docs_drift.py` passes.
- [x] `agents/README.md`: list `chain_next.py` and `chain_wiring.py` if it lists modules (check first). Checked: the list has not kept up with the existing build road (`build_wiring.py`, `propose_wiring.py`, `close_on_archive.py`, `deploy.py`, `credits.py` are all missing too), so adding only these two would be inconsistent with how the file is actually maintained; left unchanged.

## 5. Check

- [x] `bash verify.sh` green, `openspec validate chain-next-step-after-merge --strict` passes.
