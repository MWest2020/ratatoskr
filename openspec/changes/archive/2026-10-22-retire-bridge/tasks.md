# Tasks

- [x] Delete `orchestrator/bridge.py`.
- [x] `orchestrator/README.md`: remove the bridge section and say that builds
      start from the chat with `!build` (see `docs/how-to/build-from-chat.md`).
- [x] Root `README.md`: the line about `orchestrator/bridge.py` points to
      `!build` instead.
- [ ] `bash verify.sh` is green, and `grep -rn "bridge.py"` outside
      `openspec/changes/archive` finds nothing. **Not run**: this sandbox
      denies `bash verify.sh` (and any `python3 scripts/...` invocation)
      outright, so a human or CI must confirm. The grep already comes back
      clean except for this change's own proposal/tasks/spec (which describe
      the removal) and the explanatory notes left in both READMEs.
