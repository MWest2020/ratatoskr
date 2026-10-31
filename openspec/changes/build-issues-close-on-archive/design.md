## Decisions

- **Scope is the change id.** An issue is matched by its exact title, `build: <change>` or `propose: <change>`, as `issues.open_titled` already does for `propose:`. No fuzzy matching: a wrong close is worse than a missed one, and a missed one still shows in the digest.
- **One closer, two triggers.** Archive (by the chain or by hand) and removal from `main` both end in the same function, which closes with a comment that names where the change went. The pointer lets someone reading a closed issue find out why it closed.
- **Pointer by case.** Archived: the archive path. Removed or split: the PR that did it. If that PR cannot be found, the comment says so rather than inventing one.
- **Close only open issues.** Already-closed issues are left alone, so the closer is idempotent and a listener restart does not comment twice.
- **A failed close says why.** A `gh` failure is logged with its reason, not swallowed (AGENTS.md: silent failure is the fault).

## Rejected alternatives

- **Keep closing by hand from the coding session.** That is what happened for #305, #80 and #104; the point is that the factory tidies up without a human.
- **Extend only the existing `propose:` close to `build:`.** Fixes the chain's own archive but not hand-archives or splits, which are exactly the cases seen.

## Open

How a change leaving `main` outside the chain is detected (merged-PR watch vs. comparing `openspec/changes/` each tick) is not decided; see the proposal.
