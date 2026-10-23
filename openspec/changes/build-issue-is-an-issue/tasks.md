# Tasks

## 1. The check
- [ ] `agents/build.py`: a function that asks `gh` whether a number is an open
      issue on the repository (not a PR, not closed). Proof: new cases in
      `agents/test_build.py` with a faked runner: an open issue passes; a PR and
      a closed issue each fail.

## 2. The wiring
- [ ] `agents/build_wiring.py` `try_build`: a given number that fails the check
      leads to a fresh build issue, and the channel says the number was not an
      open issue and which issue is used. Proof: a test in `agents/test_build.py`
      that passes a PR number and asserts a new issue is created, the build
      starts on it, and the channel line names both numbers.
- [ ] A given number that is an open issue is used as before. Proof: a test that
      asserts no issue is created and the build starts on the given number.

## 3. Docs
- [ ] `docs/how-to/build-from-chat.md`, section "What the listener checks":
      a given number must be an open issue, else a fresh build issue is opened
      and the channel names both numbers. Proof: the docs-drift gate passes.
      (Added 2026-10-23 after the reviewer failed the first build for this gap.)

## 4. Gates
- [ ] `bash scripts/verify.sh` is green (line limit, pin check, tests).
