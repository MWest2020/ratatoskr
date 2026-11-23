# Design: the read shell

## The choice: one wrapper, not `git`/`gh` prefixes

The chat turn runs `claude -p --permission-mode dontAsk` with `--allowedTools`
from the handbook definition (providers.py). Claude Code's Bash rules match a
command prefix. The obvious version, `Bash(gh pr list:*)` plus
`Bash(git log:*)`, bounds the command but not its arguments, and the arguments
are where the danger is:

- `git log --output=<file>` writes a file.
- `gh` is logged in with Mark's token from `~/.config/gh/hosts.yml`. Its scopes
  include `repo` and `delete_repo`, and `providers.agent_env` keeps `HOME`, so
  any `gh` subcommand the prefix lets through runs with that token.
- `--repo` accepts any owner, including repositories that are off-limits.

So the rule names one program, and that program decides everything else:

- The owner is fixed: `MWest2020`. The model passes a repository name, checked
  against `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`.
- Six subcommands. Each maps to one fixed argv list (`argv()`, a pure function
  pinned by the tests), run without a shell. Numbers are bounded, and a label
  goes in as `--label=<value>` so it can never be read as a flag.
- Output is capped at 40 lines and says how many lines it dropped. A failure
  prints the subcommand and gh's first stderr line and exits non-zero, so it
  never looks like an empty answer.

The token stays reachable by the wrapper process and not by the model: Read is
path-scoped to the listener tree, and Bash is only this program.

### Rejected alternatives

- **`git`/`gh` prefix rules.** Rejected for the reasons above.
- **A local mirror of the repos, fetched on a timer.** Rejected: it needs a
  fetcher, a directory per repo and a staleness story. GitHub is already the
  source for PRs and checks, so one source is simpler than two.
- **A dedicated read-only fine-grained token.** Better, and it would make the
  wrapper's argv list a second line of defence instead of the first. It needs
  Mark to create the token. This is a follow-up, not a blocker.
- **Marker-based lookups (`!lees …`) executed by the listener**, like
  `!route`. Rejected: that needs a second model turn to read the result, and
  the claude CLI already has that loop.

## The guard: no other Bash in a chat turn

`bootstrap.build_agents` refuses an agent whose chat `allow` holds a Bash entry
other than the exact rule. The refusal is logged with the entry. Every chat
facet in the handbook today denies Bash, so this changes nothing for existing
agents. It pins down that a chat agent does not get a free shell by a one-word
edit.

A definition that allows the rule but keeps `Bash` in `deny` would have its
shell silently refused, because deny wins. The listener logs that
contradiction at start-up. It does not refuse the agent over it.

## Open risk: does the prefix rule hold?

The boundary between "the wrapper" and "any command" is Claude Code's matching
of `Bash(<prefix>:*)`. Its documentation says operators such as `&&` are
understood, so a prefix rule does not approve `cmd && other`. Not verified
here:

- `;` chaining;
- `$(...)` substitution;
- `>` redirection.

The building session's auto-mode classifier refused to spawn `claude -p` with
bypass attempts. That is a smoke test for the gate's owner, and it is in
tasks.md. Under `dontAsk`, anything the matcher does not approve is refused,
so the failure mode to rule out is a wrong approval, not a prompt.
