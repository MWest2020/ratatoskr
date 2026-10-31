## 1. Implementation

- [ ] 1.1 Close open `build: <change>` and `propose: <change>` issues with a pointer comment when a change is archived. Proved by `agents/test_propose_archive.py` (`CloseOnArchive`, extended: a merged archive closes both a `build:` and a `propose:` issue, and the comment contains the archive path).
- [ ] 1.2 Do the same when a change is removed from `main` without archive; the comment names the superseding PR. Proved by a new test in `agents/test_propose_archive.py`.
- [ ] 1.3 Already-closed issues are not touched and a repeat run comments nothing. Proved by a test with an empty `open_titled` result and a second call.
- [ ] 1.4 A failing `gh` close is logged with its reason. Proved by a test whose `close` raises, asserting the log line.

## 2. Docs

- [ ] 2.1 Update `docs/how-to/propose.md` (section "After a build: the next step, and the archive": now `build:` too, and removal) and `docs/how-to/build-from-chat.md` (section "The factory tidies up after itself"). Check: Grep for "propose: <change>" under `docs/` shows no stale statement.

## 3. Check

- [ ] 3.1 `bash scripts/verify.sh` passes (includes the 200-line limit) and `openspec validate build-issues-close-on-archive --strict` passes.
