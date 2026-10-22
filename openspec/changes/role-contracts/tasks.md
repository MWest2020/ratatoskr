# Tasks

## 1. Decide
- [x] **Mark.** Use the contract only, on top of OpenSpec, and pilot it with
      architect, bouwer and reviewer. Mark, 2026-10-22.

## 2. The prompt is found at all
- [x] `fetch_def` accepts `## Chat facet` and `## Chat-facet`, and
      `build_agents` refuses an agent without a prompt (cc5c600). After the
      restart all 7 agents with a blockquote have a prompt again; roodteam is
      refused.
- [x] `agents/test_parse_def.py`: the real layout, both heading forms, no
      swallowing of the next section, and the refusal. Verified with the fix
      removed: 3 failures.

## 3. The contract reaches the model
- [x] `agents/defparse.py`: `section`, `blockquote` and `parse_def`, pure and
      out of `bootstrap.py`.
- [x] The contract is appended after the prompt and only when both exist.
      Tests cover all three cases.
- [x] Checked against the handbook branch: architect, bouwer and reviewer each
      get their contract after their prompt.
- [x] `verify.sh` is green; deploy the listener tree.

## 4. The handbook (Mark's gate)
- [ ] Handbook PR: a `## Contract` for architect, bouwer and reviewer, the
      index section on role contracts, bouwer's chat facet saying "a DECIDED
      design", and roodteam's prompt as a blockquote. **Mark merges.**
- [ ] After the merge: wait until `fetch_def` serves it, restart, and check
      that the three prompts contain `YOUR CONTRACT` and that roodteam starts.

## 5. The pilot
- [ ] One real change goes from architect (decision) to bouwer (change and
      readiness check) to reviewer (verdict). Record where an agent still took
      something that was "not mine".
- [ ] Archive this change.
