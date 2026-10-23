# SPDX-License-Identifier: MIT
"""Long-lived children outlive a listener restart.

2026-10-23: a deploy restarted the listener four minutes into a habitat chain
and the chain died with it. `start_new_session` gives a child its own session,
not its own cgroup, and the unit's KillMode=control-group stops the whole
cgroup. `systemd-run --user --scope` moves the child into a transient scope of
its own; it execs the command, so the pid the state file keeps stays valid.

Only for children whose pid is persisted and adopted after a restart (chains,
propose sessions, the factory). Without systemd-run (tests, another host) the
command runs as before.
"""
import os
import shutil

SCOPE = ["systemd-run", "--user", "--scope", "--quiet", "--collect"]


def argv(cmd, which=shutil.which, env=os.environ):
    """`cmd`, wrapped in its own scope when a user systemd is reachable."""
    if which("systemd-run") and env.get("XDG_RUNTIME_DIR"):
        return SCOPE + list(cmd)
    return list(cmd)
