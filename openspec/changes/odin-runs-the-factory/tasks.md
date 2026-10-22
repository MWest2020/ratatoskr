# Tasks

## 0. Ground
- [x] **Mark.** Odin builds itself, OpenSpec-driven, consulted, traceable;
      merge and deploy without him (alma excluded); odin creates roles and
      channels, closing goes to Mark; the factory is agent → skills → tools.
      Mark, 2026-10-22.
- [x] Credentials: `claude-oauth-token` in namespace `agents`, created
      2026-09-05, valid one year. The 8-hour file is not in use.
- [x] The standup warns 30 days before the token expires (around
      2027-08-05); a read error is said as one. `dispatch-watch.sh` no longer
      pushes the 8-hour file, and pins worker image 750346e.

## 1. Odin builds
- [ ] `agents/factory.yml`: the repos odin may build on, the daily build
      budget, the pinned worker image.
- [ ] `agents/build.py`: parse `!build <repo> <change>`, check repo, change
      and issue, run `chain.sh` through `ssh jumpy` with fixed argv, and
      comment each role's verdict on the issue. Tests with fakes.
- [ ] A `propose` run for work without a change.
- [ ] Odin learns `!build` from a generated clause, and only when the
      factory config allows it.
- [ ] Live: one small change on ratatoskr goes through the chain, with every
      verdict on its issue.

## 2. Merge
- [ ] After four PASS verdicts: a PR from the builder branch; merge once every
      check passes (awk guard); close the issue with the merge link.
- [ ] Habitat docs: "Mark always merges" becomes the new rule, with the
      reason.

## 3. Deploy
- [ ] wordsworth: after the main image build, bump the api and init-job
      digests together in homelab and push; ArgoCD syncs. alma is not on the
      path list.
- [ ] Live: one wordsworth change ends on the cluster without Mark.

## 4. Factory
- [ ] Skill-forge: each SKILL.md declares the tools it needs; the register
      carries them.
- [ ] Handbook gate: a role's `tools.allow` equals base ∪ its skills' tools.
- [ ] `orchestrator/factory.py` replaces `create-agent.py`: a template, the
      derived tools, the local gate run, identity, keys, channel and
      membership.
- [ ] `!role` and `!channel` for odin; `!yes` from Mark's current pubkey for
      closing and for changes to an existing role.
- [ ] The handbook operating agreements: new roles by odin, closing by Mark.

## 5. Skills reach the agent
- [ ] Habitat worker: the role's skills in `.claude/skills`.
- [ ] Chat turn: skill descriptions in the prompt.

## 6. Archive
- [ ] Archive this change when phases 1 to 5 run live.
