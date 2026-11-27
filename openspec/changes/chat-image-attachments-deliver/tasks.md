# Tasks

Part 3 of the split of `chat-image-attachments`. Queued behind the other open
work (Mark, 2026-11-02): not built before `agent-image-to-chat` is archived.

## 1. Gate
- [ ] **Gate D: an agent key reads Mark's blob** (host, before the build).
      Proof: the exact `buzz media get` invocation, the CLI version, a
      byte-identical read of a blob uploaded by mark under an agent identity,
      and a 404 for an unknown hash, recorded in design.md. If the read is
      refused, amend design.md first.

## 2. Delivery
- [ ] `agents/attachments.py`: images from the triggering message only, and
      only when its pubkey is Mark's; `buzz media get` under the turn's agent
      key with a 5 MiB ceiling; magic bytes; sha256 equal to the tag's `x`;
      written to `./.turn-media/<turn-id>/` with the extension from the magic
      bytes. Proof: `agents/test_attachments.py` covers delivery from the
      recorded event, a message by an agent pubkey (nothing fetched, asserted
      on the runner), a relay 404 (expired), another relay error, wrong magic
      bytes, a hash mismatch, and a body over 5 MiB.
- [ ] `agent_turn.run_turn` adds the path line to the prompt and removes the
      directory in a `finally`; a failed delivery posts the reason and skips
      the turn; the listener sweeps `./.turn-media/` at start. Proof: tests
      for cleanup after success, after an exception, after a timeout and on
      the consult path; a failed delivery posts once and starts no
      `claude -p`.
- [ ] `.turn-media/` in `.gitignore`. Proof: the diff.
- [ ] `agents/listener.py` stays at or under 200 lines. Proof:
      `scripts/line_limit.py` green.

## 3. The seam
- [ ] One test runs `chat/imeta.py` and `agents/attachments.py` on
      `chat/testdata/imeta-event.json` and the bytes of a fake relay. Proof:
      `agents/test_attachments_chain.py`, shown to fail when the tag's `x` and
      the bytes disagree, and when the parser is bypassed.

## 4. Live
- [ ] Mark sends an image message to an agent whose model passed gate 2
      (from the chat once `chat-image-attachments` is live, or from any
      client that attaches through the relay); the answer describes the
      image and `./.turn-media/` is empty afterwards. Proof: the run on the
      issue.

## 5. Docs
- [ ] `docs/how-to/attach-images.md` (or `send-an-image.md` if the UI part is
      not built yet): what the agent sees, that only Mark's own images are
      read, and each delivery failure as it appears in the channel.
- [ ] `docs/how-to/troubleshooting.md`: "the agent says image expired" and
      "hash does not match".
