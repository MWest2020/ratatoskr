## Decision

The check lives in `agents/build.py` as one function that asks `gh` about the
number and says whether it is an open issue. `try_build` in
`agents/build_wiring.py` calls it when a number was given; when it fails, the
code takes the existing no-number path (open a fresh issue) and the channel
line names the rejected number and the new one.

The check is made by the listener, not the model, like every other `!build`
condition (see the header of `agents/build.py`). The runner is injected, so
tests fake `gh`.

GitHub serves pull requests through the issues API as well, so a lookup of the
number alone is not enough: the answer has to be read for "is a pull request"
and for its state. The tasks name the test that pins each case.

The requirement is an ADDED one in `habitat-bridge`, not a change to the
existing gatekeeper requirement, which `odin-runs-the-factory` is still
modifying.

## Rejected alternatives

- **Refuse the build when the number is not an open issue.** Safe, but it stops
  a build over a wrong number and needs another message. The decided behaviour
  keeps the chain moving and keeps the trail on a real issue.
- **Fix it in the prompt** (tell odin to check numbers). Every other `!build`
  condition is checked in code, not in a prompt; a prompt rule is how #207 got
  through.
- **Silently open a fresh issue.** Whoever gave the number would not know the
  trail is elsewhere. The channel says so.
