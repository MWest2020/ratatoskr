## 1. Implementation

- [ ] 1.1 A tick reads `openspec/changes` and `openspec/changes/archive` per repository with an open `build:`/`propose:` issue (one `gh api` call each) and closes an issue when its change id is absent from `changes` and exactly one `YYYY-MM-DD-<id>` archive directory exists; the comment contains the archive path. Proved by the seam test below, case "archive": fake main with the change archived, a `build:` and a `propose:` issue both end commented then closed.
- [ ] 1.2 Removal without archive is never closed, only logged. Proved by the seam test, case "removal": fake main where the change is gone and no archive exists; the issue stays open and a log line says so.
- [ ] 1.3 A change still in `openspec/changes` is untouched. Proved by the seam test, case "untouched".
- [ ] 1.4 A `gh` error or rate limit skips the tick for that repository and logs the reason; nothing is closed. Proved by the seam test, case "gh failure": fake main whose `gh api` fails, asserting no close and the logged reason.
- [ ] 1.5 Restart safety: a fresh process with empty state closes an already-archived change's issue, and a second tick comments nothing. Proved by the seam test, case "empty-state restart", with two ticks.
- [ ] 1.6 The dated archive id is resolved from the archive listing, not carried through `propose_git.archive` or `state.json`; a `merging` entry written before this change works. Proved by the seam test, case "old merging entry" (state without the dated id).
- [ ] 1.7 The existing `propose:` close in `after_merge` goes through the same closer. Proved by `agents/test_propose_archive.py` (`CloseOnArchive`) still passing, extended with a `build:` issue.
- [ ] 1.8 Only repositories with an open build issue are polled, at most one call pair per repository per tick. Proved by the seam test counting calls on the fake main with two issues in one repository.
- [ ] 1.9 A failing `gh` close is logged with its reason and the other issues are still processed. Proved by a test whose `close` raises, asserting the log line and the second close.

The seam test runs the poller against a fake main (the `gh api` runner replaced) and calls both the listing side and the closing side (AGENTS.md: a seam needs a test that calls both sides). It lives in `agents/test_propose_archive.py` or a new `agents/test_close_on_archive.py`.

## 2. Docs

- [ ] 2.1 Update `docs/how-to/propose.md` (section "After a build: the next step, and the archive": now `build:` too, detection from main every 30 minutes, removal is logged and not closed) and `docs/how-to/build-from-chat.md` (section "The factory tidies up after itself"). Check: Grep for "propose: <change>" under `docs/` shows no stale statement.

## 3. Check

- [ ] 3.1 `bash scripts/verify.sh` passes (includes the 200-line limit) and `openspec validate build-issues-close-on-archive --strict` passes.
