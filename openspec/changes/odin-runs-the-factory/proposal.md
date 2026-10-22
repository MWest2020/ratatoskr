# Odin runs the factory

## Why

Mark, 2026-10-22:

> I want a channel where I can talk to odin and he will distribute work or
> consult others. So we need shells and worktrees etc. Basically I want to
> build on projects like wordsworth, but never have to deal with a terminal or
> update my site.

And his answers to the questions that followed:

1. *"definitely odin may build itself. My repos, whenever possible or when it
   makes sense, openspecced, consulted and yes. build I want traceability, but
   autonomous eco."*
2. Merge and deploy without him: *"absolutely"*, with alma (production)
   excluded as proposed.
3. Archive the quiet channels. Done in 34cc540.
4. *"I also want a factory pattern. odin can decide for new roles if need be,
   and new channels. closing should be consulted with me. also, factory
   pattern should be agent -> skills -> tool usage. clearly defined."*

## What is there, measured 2026-10-22

| piece | state |
|---|---|
| Building in a cage | habitat: architect, builder, reviewer and security as K8s Jobs. Output is a pushed branch per run; `dispatch/chain.sh` chains the four roles. |
| Credentials | `claude-oauth-token` (one year, created 2026-09-05) is the default. The 8-hour file is gone. |
| Starting a build from chat | `orchestrator/bridge.py` exists but is **not deployed**, and it only accepts Mark's **old** pubkey. |
| PR, merge, verdict back | **None.** habitat never opens a PR or merges, and the verdict never reaches the chat. |
| Work trail | the shared room: issue per piece of work, comments, labels (shared-room). |
| A new role | `orchestrator/create-agent.py`, which is stale: wrong paths, and it writes no model, tools or skills, so every gate refuses it. |
| Skills | declared in the definition and checked against the register, but **never delivered** to the agent. |

## What changes, in phases

1. **Odin builds.**
   - Odin may end an answer with `!build <repo> <change>`.
   - The listener checks the request, not the model:
     - the repository is Mark's;
     - the OpenSpec change exists and validates;
     - the work has an issue.
   - It then runs the habitat chain (architect, builder, reviewer, security).
     Each step's verdict becomes an issue comment.
   - Work without a change first gets one: a `propose` run writes it, and the
     `apply` run builds it.
2. **Merge without Mark.**
   - When every role passes, the listener opens the PR.
   - It merges once every CI check passes.
   - All of this goes on the issue.
3. **Deploy without Mark.**
   - For repositories with a GitOps release chain, a merge to main ends on
     the site by itself. wordsworth gets the same chain: the api and init-job
     digests are bumped together in homelab.
   - **alma is never a target.**
4. **The factory: agent → skills → tools.**
   - A role is generated from one template and checked before it exists.
     - Its **skills** come from the skill register.
     - Each skill declares the **tools** it needs.
     - A role's tools are exactly what its skills need, plus a declared base.
       The gate refuses anything beyond that.
   - Odin may create roles and channels (`!role`, `!channel`).
   - **Closing a role or channel, or changing an existing role's mandate or
     tools, waits for Mark's yes in the chat.**
5. **Skills reach the agent.** A role's skills are delivered to its turn, not
   only declared.

## Invariants that stay

- **No agent changes its own definition, keys or the relay configuration.**
  Odin creates other roles; its own stays Mark's.
- **Chat turns get no free shell.** Building happens in habitat's cage; the
  read shell stays the only Bash in chat.
- **alma stays out of reach**, as in the owner's auto-mode rules.
- **Git is the truth, and every build has an issue.** An untracked build does
  not start.
