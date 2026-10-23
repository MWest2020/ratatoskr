# SPDX-License-Identifier: MIT
"""A session the hub started wakes the hub when it is done.

2026-10-23: odin started a wordsworth session and planned to consult architect
and reviewer "when the report arrives". The report is posted under odin's own
key, and the listener never gives a turn on an agent's message (the loop
guard), so the plan could never fire; the coding session had to nudge odin.

Now the listener gives the hub ONE follow-up turn in that channel after each
session it started, with the report as the last message. That turn may consult
or build, but may not start another session: a session that wakes a turn that
starts a session would be a loop that costs money while it runs.
"""

PROMPT = ("Your work session `{type}` has finished; its report is the last message "
          "above. Do now what you said you would do with it (consult, build, or tell "
          "Mark where it stands). Do not start another session from this answer.")


def wake_hub(reg, hub, fetch, run_turn, log=print):
    """Drain `reg.finished`; one follow-up turn per session the hub started."""
    while reg.finished:
        s = reg.finished.pop(0)
        if s.get("starter") != hub:
            continue
        msgs = fetch(s["cid"])
        if not msgs:
            log(f"[listener] session {s['type']} done, but #{s['cname']} unreadable — "
                "hub not woken", flush=True)
            continue
        run_turn(hub, s["cname"], s["cid"], msgs, len(msgs) - 1,
                 PROMPT.format(type=s["type"]), s.get("requester") or "", "",
                 "session-done", followup=True)
