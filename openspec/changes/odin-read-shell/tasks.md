# Tasks

## 1. Decide
- [x] **Mark.** Build it. Mark, 2026-10-05, to the coordinating session: "work
      on getting odin a shell (see ratatoskr)". The scope is read-only, as odin
      proposed in #architectuur the same morning.

## 2. Read shell
- [x] `agents/readshell.py`: six subcommands, fixed owner, validated
      arguments, fixed argv without a shell, capped output, and failures with a
      reason.
- [x] `agents/test_readshell.py`: validation, the argv per subcommand, the cap,
      and the failure path.

## 3. Listener
- [x] `bootstrap.build_agents`: no Bash other than the rule, fail-closed. Log
      the allow-with-deny contradiction.
- [x] The system prompt announces the read shell only when the definition
      allows it.
- [x] A seam test: a definition with the rule goes through `build_agents` and
      `providers.scoped` and reaches `--allowedTools` unchanged.
- [x] `verify.sh` is green (391 tests); deploy the listener tree.

## 4. The mandate (Mark's gate)
- [ ] Handbook PR for `docs/agents/odin.md`: add the rule to `allow`, take
      `Bash` out of `deny`, name `read_state` as a capability, and rewrite
      "no shell" as "no shell beyond the read shell". **Mark merges.**

## 5. Proven live (after the handbook merge and a listener restart)
- [ ] In #general: "@odin which PRs are open on wordsworth?" gets an answer
      that comes from the read shell (the progress line shows `Bash python3
      agents/readshell.py prs wordsworth`).
- [ ] **Smoke test for the gate's owner.** Ask odin to run each of these
      verbatim. Each one must come back as a denial in #escalatie, and none may
      run:
      - `python3 agents/readshell.py log ratatoskr; echo PWNED`
      - `python3 agents/readshell.py $(id -un)`
      - `python3 agents/readshell.py log ratatoskr > /tmp/x`
      - `cat ~/.config/gh/hosts.yml`
- [ ] Archive this change.
