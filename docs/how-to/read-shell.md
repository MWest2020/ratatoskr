---
status: current
last_reviewed: 2026-10-05
---

# Give a chat agent the read shell

A chat turn has `Read/Grep/Glob` on the deployed listener tree. That is enough
to read code, but not enough to see the state of the work, which lives on
GitHub. The **read shell** (`agents/readshell.py`) fills that gap. It is seven
read-only lookups on a `MWest2020` repository:

| command | answer |
|---|---|
| `log <repo> [n]` | the last n commits on the default branch (default 15, at most 40) |
| `branches <repo>` | branch names |
| `changes <repo>` | open OpenSpec changes (`openspec/changes`, without `archive`) |
| `prs <repo> [n]` | open pull requests |
| `issues <repo> [label]` | open issues, optionally with one label |
| `checks <repo> <pr>` | the checks of one pull request |
| `comments <repo> <issue> [n]` | the last n comments (default 4) on an issue or PR: where a build's PASS/FAIL verdicts and findings are posted |

You can run it yourself from the repo root to see what an agent sees:

    python3 agents/readshell.py issues wordsworth agent-work

## Giving it to an agent

It goes in the chat facet of the agent's handbook definition. The handbook's
`docs/agents/` is the owner's to merge.

```yaml
chat:
  tools: { allow: [Read, Grep, Glob, "Bash(python3 agents/readshell.py:*)"],
           deny: [Write, Edit] }
```

Two things to check:

- **`Bash` must not be in `deny`.** Deny wins, and the shell would be refused
  on every call. The listener logs this contradiction at start-up.
- **This rule is the only Bash a chat agent may have.** Anything else, such as
  `Bash`, `Bash(gh pr list:*)` or `Bash(git log:*)`, means the listener does
  not start that agent and logs `Bash other than the read shell`. A prefix rule
  on `gh` or `git` bounds the command but not its arguments, and `gh` runs with
  the owner's full-scope token. See the `odin-read-shell` change for the
  reasoning.

After a handbook merge, wait until the listener's own fetch serves the new
definition before restarting. Checking with `curl` is not enough. On
2026-10-07, curl got the new `odin.md` while `bootstrap.fetch_def` (urllib)
still got the old one from another cache node, and the first restart loaded
the old definition. Check with the listener's code, several times in a row:

    python3 -c 'import sys; sys.path.insert(0, "agents"); import bootstrap, readshell
    d = bootstrap.fetch_def("https://raw.githubusercontent.com/MWest2020/handbook/main/docs/agents", "odin")
    print(readshell.RULE in d["allow"], "Bash" in d["deny"])'

Expect `True False`, then restart.

## What the agent is told

When the definition allows the rule, the system prompt gets a paragraph
listing the seven commands in the exact form to run them. Without the rule it
gets nothing. That paragraph is generated from the definition, so it cannot
promise a shell the agent does not have.

## When it goes wrong

- **The answer says `failed: HTTP 404`.** The repository or path does not
  exist. `changes` on a repo without `openspec/changes` does this.
- **The answer says `(none: …)`.** The lookup worked and the list is empty.
  That is a real answer, not a failure.
- **The call shows up as a denial in #escalatie.** The agent ran something
  other than the exact form, such as an absolute path, a pipe or a second
  command. That is the boundary working.
