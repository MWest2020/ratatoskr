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
- [x] `agents/factory.yml`: the repos odin may build on, the daily build
      budget, the pinned worker image.
- [x] `agents/build.py`: parse `!build <repo> <change>`, check repo, change
      and issue, run `chain.sh` through `ssh jumpy` with fixed argv, and
      comment each role's verdict on the issue. Tests with fakes.
      Done as build.py (checks), build_runner.py (detached chain, follows
      its output), build_wiring.py (issue first, every event on the issue);
      the guards are mutation-checked.
- [ ] A `propose` run for work without a change.
- [x] Odin learns `!build` from a generated clause, and only when the
      factory config allows it.
- [ ] Live: one small change on ratatoskr goes through the chain, with every
      verdict on its issue.

## 2. Merge
- [x] After four PASS verdicts: a PR from the builder branch; merge once every
      check passes; close the issue with the merge link. (build_merge.py reads
      GitHub's check buckets instead of a piped exit code; zero checks is no
      merge.)
- [x] Running chains and waiting PRs survive a listener restart (state.json:
      pid, events seen, PR).
- [x] Live: retire-bridge (ratatoskr#157). odin started it from #general,
      all four roles passed in about 16 minutes, and each verdict is on the
      issue. PR #158 was opened by hand with the listener's own phase-2 code,
      because the chain ran under the phase-1 listener. After a restart the
      listener took the PR over from state.json, waited for verify and
      docs-gates, and merged it (c08a1d1, 2026-10-22 13:56); the issue closed.
- [ ] Habitat docs: "Mark always merges" becomes the new rule, with the
      reason.

## 3. Deploy
- [x] wordsworth: after the main image build, bump the api and init-job
      digests together in homelab and push; ArgoCD syncs. alma is not on the
      path list. (agents/deploy.py: image, push, sync and verify, one step per
      tick, persisted in state.json. The bump is all or nothing. Tests run
      against a real git remote and are immune to the hook's GIT_DIR.)
- [x] Gap from the first build: habitat builders may run `bash verify.sh` and
      `python3 -m unittest` (habitat builder-runs-repo-gates, image e01d069).
- [ ] Live: one wordsworth change ends on the cluster without Mark.

## 4. Factory
- [x] Skill-forge: each SKILL.md declares the tools it needs; the register
      carries them.
- [x] Handbook gate: a role's `tools.allow` equals base ∪ its skills' tools.
- [x] `orchestrator/factory.py` replaces `create-agent.py`: a template, the
      derived tools, the local gate run, identity, keys, channel and
      membership.
- [x] `!role` and `!channel` for odin; `!yes` from Mark's current pubkey for
      closing and for changes to an existing role.
- [ ] The handbook operating agreements: new roles by odin, closing by Mark.

## 5. Skills reach the agent
- [ ] Habitat worker: the role's skills in `.claude/skills`.
- [ ] Chat turn: skill descriptions in the prompt.

## 6. Archive
- [ ] Archive this change when phases 1 to 5 run live.
