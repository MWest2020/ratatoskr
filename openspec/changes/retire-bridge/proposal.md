# Retire the old bridge

## Why

`orchestrator/bridge.py` was the first road from a chat message to habitat.

- **It was never deployed.** No unit exists for it.
- **It only accepts Mark's old pubkey** (`821de7…`, rotated 2026-08-28), so it
  cannot work.

Since odin-runs-the-factory phase 1, the road is `!build`, which the listener
checks (`agents/build.py`). A second, dead road next to it only misleads
whoever reads the repo.

## What changes

- Remove `orchestrator/bridge.py`.
- Update `orchestrator/README.md` and the root `README.md` where they describe
  the bridge: point to `docs/how-to/build-from-chat.md` instead.
- No behaviour changes. Nothing ran the bridge.
