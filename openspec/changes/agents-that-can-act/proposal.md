# Agents that can actually do something

## Why

Mark, 2026-09-21: *"ik krijg net van Odin dat hij geen web fetch kan, of geen pr
kan openen. dat moet echt kappen. […] anders kan ratatoskr in de prullenbak."*

Odin is not being difficult. It is reporting the system accurately. Three
separate walls, and they need three separate answers:

| wall | where it lives | what it blocks |
|---|---|---|
| tools | `tools.allow` in the handbook definition + `--permission-mode dontAsk` | `WebFetch` is refused and logged as a `permission_denial` |
| credentials | `providers.ENV_KEEP` | no `GITHUB_TOKEN`, no ssh-agent, so `gh` cannot authenticate |
| time and workspace | `MAX_TURN_S = 150`, no checkout | a branch, a commit and a push do not fit |

The asymmetry is the finding: **every work-session type in `sessions.yml` has
`WebFetch`; not a single chat agent does.** And a `build` session already opens
pull requests, from a fresh worktree, behind a `pre-push` hook. The capability
exists one layer up. The chat turn is the thin layer.

So the question is not "may an agent do more". It is **where capability should
live**, and the answer is different per wall.

## What changes

**1. Reading the web is a tool, and it goes in the definition.** `WebFetch` is
added to the definitions of the agents that need it — the handbook is Mark's
gate, and that is the right gate for "may this role read the internet".

**2. Acting on a repository does NOT get a credential in the chat turn.** An
agent that wants a pull request writes a `!sessie build` marker. The session has
the worktree, the tools, the time budget and the `pre-push` hook that refuses
anything but its own branch. `build` becomes usable for more than this repo.

**3. No MCP server for this.** See `design.md`: it would be a new trust boundary
holding credentials, and it buys nothing that a session does not already do.

## The risk this introduces, named

An agent that can fetch a page **and** write markers can be steered by that
page. `!sessie build <anything>` inside a fetched document is an instruction
written by a stranger. Today this is impossible because no chat agent can fetch.

That is not a footnote; it is the reason this change needs a rem. See
`design.md`.

## Not doing

- Giving a chat turn `Bash`, a token, or a writable checkout.
- Widening `ENV_KEEP`. It exists because the listener carries the nsec of every
  agent, and one successful injection reads `/proc/self/environ`.
