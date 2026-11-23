# Design: odin runs the factory

## One build road: habitat

There are two ways to write code today. One is the `build` work session, which
runs in a worktree on the agent host and ends in a PR. The other is habitat,
which runs a Job in the cluster per role and ends in a branch.

**Choice: habitat is the only road for building**, and odin starts it.

- **Rejected: the `build` session.** It runs on the agent host, next to
  Mark's gh token, the age key and every agent nsec. A cage that is a separate
  Job with its own service account is a real boundary; a worktree on the same
  host is a directory.
- **What stays:** the `build` session type remains for Mark, but odin does not
  get it.

## Who checks a build: the listener, not the model

`!build <repo> <change>` is a marker in odin's answer, the same pattern as
`!sessie` and `!route`. The listener acts only when all of these hold:

1. **The repository is Mark's:** `MWest2020/<repo>`, a name from a fixed list
   in `agents/factory.yml`.
2. **The change exists and validates:** `openspec/changes/<change>/` on the
   repo's main, and `openspec validate --strict` passes in the propose run's
   output.
3. **There is an issue:** the build belongs to a room issue, or the listener
   opens one first.
4. **The budget holds:** at most N builds a day, set in `factory.yml`.

Rejected: letting odin run `dispatch.sh` through a shell. That would put the
whole decision in the model, which is a boundary as strong as today's model.

## The chain and its trail

The listener calls `chain.sh` through the `ssh jumpy` path that
`dispatch-watch.sh` already uses. It is fixed argv, with the pinned worker
image. After each role it adds an issue comment:

- the role and its verdict (PASS or FAIL, with the summary from the run
  report);
- the branch.

A FAIL stops the chain:

- The issue says why.
- Bouwer gets one repair round through the room hand-off. The habitat
  orchestrator's "at most 2 rounds" becomes code: the listener counts.

## Merge: after the cage, after CI

1. **The PR.** Every role passes, so the listener opens a PR from the builder
   branch. The issue number and the four verdicts go in the body.
2. **The checks.** The listener waits for the PR's checks. It merges only
   when every one of them passes, using the awk guard from the handbook,
   never `grep -qv`.
3. **The issue is closed** with a link to the merge.

This replaces "Mark always merges" in habitat's documentation. That is
Mark's decision of 2026-10-22, and the habitat docs change with it.

## Deploy: GitOps, never alma

- **Where a release chain exists** (wanderer: tag, then image, then ArgoCD),
  a merge is enough.
- **wordsworth gets the same chain.** After the image build on main, the api
  and init-job digests are bumped *together* in homelab (homelab memory: never
  one without the other), then pushed, and ArgoCD syncs.
- **alma is no target:** the deploy step has a fixed list of
  ArgoCD/homelab paths, and alma is not on it.

## The factory: agent, then skills, then tools

Today a role declares tools and skills separately, and nothing links them.
The chain Mark asked for:

    role (handbook def) ──declares──► skills (from the register)
                                          │ each skill declares
                                          ▼
                                       tools it needs (SKILL.md `allowed-tools`)
    role.tools.allow  ==  base tools (Read, Grep, Glob)  ∪  ⋃ skill.tools

- **The handbook gate checks the equality,** so a role cannot quietly hold a
  tool no skill needs.
- **`factory.py` replaces `create-agent.py`.** It generates the definition
  from the template: name, mandate, contract, chat facet, model, skills, and
  the derived tools. It runs the handbook gate locally before anything is
  created.

## What odin may decide, and what waits for Mark

| action | who decides |
|---|---|
| create a role (`!role`) | **odin**: a handbook PR, merged when the gates pass |
| create a channel (`!channel`) | **odin** |
| start a build (`!build`) | **odin**, inside the checks above |
| merge after cage and CI | **the listener**, automatically |
| deploy (not alma) | **automatically** after merge |
| **close** a role or channel | **Mark**: odin proposes, Mark says yes in the chat |
| change an existing role's mandate or tools | **Mark** |
| odin's own definition | **Mark**, always |

"Mark says yes in the chat" is a marker as well. `!yes` from Mark's pubkey
(the current one, not the old one in `bridge.py`) answers the latest
proposal.

## Skills reach the agent

The register says which skills exist. The run must also *get* them.

- **Habitat:** a role's skills are copied into the worker's `.claude/skills`.
- **Chat:** the skill's description goes into the prompt, and its content
  when it is invoked.

This follows the agent-runtime decision "skills as a per-agent subset".

## Order

1. odin builds;
2. merge;
3. deploy;
4. factory;
5. skills.

Each phase is usable on its own, and each later phase needs the one before it.
