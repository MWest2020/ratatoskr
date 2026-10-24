# SPDX-License-Identifier: MIT
"""The `!propose` marker: what counts, and what is said when it does not.
Split from propose.py for the line limit (2026-10-24, when a leading block
of markers began to fan out)."""
import re

MARKER = re.compile(r"^!propose\s+([A-Za-z0-9][A-Za-z0-9._-]{0,99})\s+"
                    r"([a-z0-9][a-z0-9._-]{2,80})\s+(\S.{0,4000})$")


FANOUT = 5   # independent changes the hub may have written at once (graph, 2026-10-24)


def read_markers(answer):
    """The `!propose` lines at the very top of the answer, at most FANOUT. Only a
    leading block counts, so a quoted marker further down never acts."""
    out = []
    for line in (answer or "").strip().split("\n"):
        m = MARKER.match(line.strip())
        if not m or len(out) == FANOUT:
            break
        out.append((m.group(1), m.group(2), m.group(3)))
    return out


def read_marker(answer):
    found = read_markers(answer)
    return found[0] if found else None


def strip_markers(text):
    """The answer without its leading block of `!propose` lines."""
    lines = (text or "").strip().split("\n")
    n = len(read_markers(text))
    return "\n".join(lines[n:]).strip()


def unread(answer):
    """A note when the first line starts with `!propose` and does not parse.
    2026-10-24: two of odin's proposals had a 400-character summary against a
    300 limit, and were dropped without a word."""
    first = (answer or "").strip().split("\n", 1)[0].strip()
    if not first.startswith("!propose") or MARKER.match(first):
        return ""
    return ("\n\n⚠ `!propose` not understood, nothing started. The first line must be "
            "`!propose <repo> <change-id> <one-line summary>`: a lowercase id of 3-81 "
            "characters, a summary of at most 4000.")
