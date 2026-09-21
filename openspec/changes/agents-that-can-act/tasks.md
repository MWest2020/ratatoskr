# Tasks

## 1. Decide
- [ ] **For Mark.** Which agents get `WebFetch`? Proposal: `odin` and
      `architect` — the two that are handed links.
- [ ] **For Mark.** Should `build` be usable for repositories other than this
      one, and which? That is a bigger right than reading.

## 2. Reading the web
- [ ] `WebFetch` into the chosen definitions (handbook PR, CODEOWNERS = Mark).
- [ ] Marker reading restricted to the first line of an agent's answer.
- [ ] Test: an answer quoting a fetched `!sessie`/`!route` marker starts nothing.

## 3. Acting on a repository
- [ ] `build` takes the target repository from the marker, bounded by an
      allow-list in `sessions.yml` — not free choice.
- [ ] The `pre-push` hook is installed in every such worktree, and a test proves
      a push to `main` is refused.
- [ ] Failure is loud: a session that cannot open a PR says so in the channel.

## 4. Explicitly not
- [ ] No `Bash` in a chat turn, no token in `ENV_KEEP`, no MCP server. Revisit
      the last one when a verb appears that a session cannot express.
