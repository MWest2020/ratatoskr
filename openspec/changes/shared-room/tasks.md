# Tasks

## 1. Decide
- [x] **Mark.** Talk to several agents at once without @, see what they do,
      with GitHub issues as the trail. Mark, 2026-10-22. Defaults for the four
      questions are in design.md.

## 2. Build
- [x] `agents/agent_turn.py`: the turn moves out of the poll loop so a
      hand-off can start one. listener.py drops 30 lines.
- [x] `agents/rooms.py`: room config, `repo#N` references, the `!handoff` and
      `!done` markers, and the hand-off targets taken from the contract.
- [x] `agents/triage.py`: haiku, `--tools ""`, and JSON validated against the
      room.
- [x] `agents/issues.py`: create, comment, relabel and close with fixed argv,
      bodies on stdin.
- [x] `agents/room_flow.py`: mention, then follow-up, then triage. No issue
      means no turn; the hop limit applies.
- [x] Tests: `test_room_flow.py` covers every path with fakes that record each
      GitHub call; `test_triage_issues.py` covers validation and argv. Checked
      with the hand-off guard and with the fail-closed issue removed: each
      test fails.
- [x] Live: `issues.py` against ratatoskr#155 (create, comment, relabel,
      close, and a body with `--label=evil` that stayed text). Triage on haiku
      put four sample messages correctly with architect, bouwer, reviewer and
      nobody.
- [x] `orchestrator/create-room.py`, and `docs/how-to/werkplaats.md`.

## 3. Live
- [x] **Mark** runs `create-room.py` (the classifier refuses adding members
      to agents). Done 2026-10-22: f7324a19, mark + 3 agents.
- [x] The id and `room:` block go in channels.yml; deploy and restart.
- [ ] Smoke test in #werkplaats: one design question goes through triage and
      gets an issue, an answer and a hand-off, all visible on the issue.
- [ ] Archive this change.
