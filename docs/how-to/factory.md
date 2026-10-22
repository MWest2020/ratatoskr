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
