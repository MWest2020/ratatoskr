# Design — where capability lives

## The three answers

### Reading the web → a tool in the definition

`WebFetch` in `tools.allow` of the agents that need it. Cheap, reversible, and
it lands where a human already approves roles (handbook, CODEOWNERS = Mark).

### Acting on a repository → a session, not a credential

`gh pr create` needs a token. A token in the chat turn's environment is
readable by anything that turn runs, and the turn's input is whatever was typed
in a public channel. The session mechanism was built for exactly this and its
fence is not a prompt:

> a `pre-push` hook in the worktree refuses everything but the session's own
> branch. *"een schrijvende sessie heeft `Bash` nodig, en dan is 'push niet naar
> main' in een prompt niets waard"* (`docs/how-to/werksessies.md`).

So: odin writes `!sessie build …`, the session opens the PR, the link lands in
the channel. What is missing today is only that `build` is bound to this repo.

### The MCP question → not now, and here is why

An MCP server offering `open_pr(repo, branch, title, body)` is attractive: narrow
verbs, credentials held by the server, every call logged. It is also a **new
trust boundary**. It holds a token, it is reachable by whatever can talk to it,
and its audit trail is one we would have to build and then trust.

A session needs none of that: the credential is the host's, the fence is a git
hook, and the outcome is a pull request a human reviews. An MCP earns its place
only for a verb a session **cannot express** — a video transcript, a vendor API
with no CLI. Opening a pull request is not such a verb.

This is a "not yet", not a "never". The trigger to revisit is a concrete verb
that a session cannot do.

## The rem: fetched text is not an instruction

With `WebFetch` in a chat agent, a page can contain `!sessie build …` or
`!route #bouw …`. The listener reads markers out of an agent's answer, so a
quoted page becomes a command.

The rule: **a marker is honoured only when the agent composed it**, never when
it appears in content the agent fetched or quoted. Mechanically the cheapest
version that actually holds: markers are read only from the **first line** of an
agent's answer, so quoted material further down is inert.

This needs a test that fetches a document containing a marker and asserts that
nothing started. Per `CLAUDE.md`: a seam between two parts, each with its own
green tests, is exactly where the failures of 11–13 September lived.

Second rem, already there and worth keeping: `starters` per session type. Even a
successfully injected marker only starts a type the agent is allowed to start.

## Rejected alternatives

**Give the chat turn `Bash` + a `GITHUB_TOKEN`.** One line of config, and it
puts a credential in the process whose input is a public channel. `ENV_KEEP`
exists because of this exact reasoning; reversing it for convenience undoes a
deliberate control.

**A longer chat turn (150 s → 20 min).** Does not solve it: there is still no
checkout and no credential, and a chat that blocks for twenty minutes is not a
chat.

**An MCP server now.** See above. It is the answer to a question we have not yet
been asked.

**Let odin ask a human to open the PR.** That is today's behaviour, and it is
what "dan kan ratatoskr in de prullenbak" is about.
