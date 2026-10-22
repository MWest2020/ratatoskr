# Tasks

- [ ] Delete `orchestrator/bridge.py`.
- [ ] `orchestrator/README.md`: remove the bridge section and say that builds
      start from the chat with `!build` (see `docs/how-to/build-from-chat.md`).
- [ ] Root `README.md`: the line about `orchestrator/bridge.py` points to
      `!build` instead.
- [ ] `bash verify.sh` is green, and `grep -rn "bridge.py"` outside
      `openspec/changes/archive` finds nothing.
