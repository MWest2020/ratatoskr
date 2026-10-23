## Why

Tonight odin passed wordsworth #207 to `!build` as the issue number. #207 was a
PR (the OpenSpec change PR), not an issue, so the merge's "Closes #207" closed
nothing and the build's trail (verdict comments, deploy lines) landed on the
wrong object. Nothing looked wrong: `!build` takes any number and trusts it.

Decided in the coding session: *"when !build gets a number, the listener checks
with gh that it is an open ISSUE (not a PR, not closed) and otherwise opens a
fresh build issue and says so in the channel."*

## What changes

- When `!build <repo> <change> <number>` carries a number, the listener asks
  GitHub (`gh`) whether that number is an open issue on the repository. A pull
  request or a closed issue does not count.
- When it does not count, the listener opens a fresh build issue, exactly as for
  a `!build` without a number, and builds on that one.
- The channel says so: the given number was not an open issue, and which issue
  is used instead.
- A number that is an open issue behaves as before.

Affected code: `agents/build.py` (the check), `agents/build_wiring.py` (use it in
`try_build`), tests in `agents/test_build.py`.

## Open questions

- When `gh` cannot be reached for the check (timeout, auth), is the number
  trusted, replaced by a fresh issue, or is the build refused? Not decided in
  the channel; the requirement covers only the answers `gh` gives.
- A number that does not exist at all: treated like a PR or closed issue (fresh
  issue)? Not stated in the decision; not in the requirement.
- Does the propose road, which also files a number, get the same check? Not
  decided; this change touches `!build` only.
