---
status: current
last_reviewed: 2026-10-22
---

# Create an agent with the factory

Odin decides new roles; the factory makes them (openspec change
`odin-runs-the-factory`, phase 4). Closing a role, or changing an existing
one, stays Mark's.

## The chain: agent → skills → tools

A role's tools are not chosen; they follow from its skills.

    tools.allow = Read, Grep, Glob + the tools of its skills (skill register)
    tools.deny  = Write, Edit, and Bash unless a skill brings a Bash rule

A capability that needs a tool is therefore a skill in skill-forge, with
`allowed-tools` in its `SKILL.md`. The handbook gate (`check_agent_tools.py`)
refuses a definition whose tools differ from what its skills need.

## The spec

    name: scout                      # new; existing or reserved names are refused
    model: haiku                     # haiku | sonnet | opus
    channels: [werkplaats]           # existing, not archived
    skills: [read-state]             # promoted skills from the register
    mandate: One paragraph.
    contract:
      takes: ...
      produces: ...
      done_when: ...
      hands_off_to: ...
      not_mine: ...
    prompt: |
      You are 'scout', ...

    uv run orchestrator/factory.py --spec role.yml --dry-run   # validate + show the definition
    uv run orchestrator/factory.py --spec role.yml             # create it

## What it does, in this order

1. **Validate and render.** This step is pure (`orchestrator/factory_def.py`).
   Any reason the spec cannot become a role is printed as JSON, and nothing
   happens.
2. **Handbook.** It writes `docs/agents/<name>.md` in its own worktree, runs
   the gate, and opens a PR. It merges the PR once every check passes.
3. **Ratatoskr.** It adds the identity to `identities.yml`, the key to
   `secrets/identities.yaml` (re-encrypted with SOPS over stdin, so no
   plaintext file is written), and the name to `agents/agents.yml`, then
   pushes that commit to main.
4. **Relay.** It adds the agent as a relay member and as a bot in each
   channel, signed by the orchestrator (the channel owner), and sets the
   agent's profile name.

The listener starts the agent after its next restart, once `fetch_def` serves
the merged definition. The steps are in `orchestrator/factory_steps.py`.
Rerunning the factory on a half-made role stops at the step that already
exists and says which.

It replaces `create-agent.py`, which pointed at `~/boomhuis`, wrote no model,
tools or skills, and signed channel changes as Mark.

## From the chat: odin's markers, Mark's `!yes`

Odin drives the factory with markers on the **first line** of its answer.
`agents/factory_wiring.py` acts on them.

| marker | what happens |
|---|---|
| `!role` + a ```` ```yaml ```` block with the spec | the factory runs in the background; on success the listener waits until the handbook serves the new definition three times in a row, then moves to main and restarts, so the agent starts |
| `!channel <name> <agent,agent> <purpose>` | the channel is created with Mark and those agents, recorded in `channels.yml`, and the listener restarts to listen there |
| `!close role <name>` / `!close channel <name>` | **only a proposal**: nothing is closed until Mark answers `!yes` in that channel within 24 hours. The `!yes` must be his own message, checked by pubkey |

On `!yes` a channel is archived on the relay and marked `archived:` in
`channels.yml`. A role leaves the run list and its identity becomes
`inactief`, while its handbook definition stays as history. Odin cannot
propose closing itself.

## Skills reach the agent (phase 5)

A chat agent's declared skills are now usable, not only declared:

- **Installed:** at listener start, `agents/agent_skills.py` copies every
  skill some agent declares from the skill-forge checkout
  (`~/skill-forge/skills/<slug>/`) into `<listener>/.claude/skills/<slug>/`.
  That is the project skills directory Claude Code reads from the turn's
  working directory, and it is gitignored. A declared skill the checkout lacks
  is logged. A skill no longer declared is removed.
- **Allowed:** each turn gets `Skill(<slug>)` for that agent's own skills only.
  Under `--permission-mode dontAsk` every other `Skill(...)` is refused, so the
  coding session's own skills in `~/.claude/skills` stay out of reach.

The habitat side is deferred on purpose: no execution facet declares a skill
yet, and a mechanism for none is built for nobody. When one does, the role's
skills go into the worker through git or the image, never as chat text.
