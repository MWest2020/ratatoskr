# SPDX-License-Identifier: EUPL-1.2
"""What a session puts in the channel at the end.

Separate from sessions.py because that file is about processes and files and this
one about text — and because otherwise both would go over 200 lines.

One rule decides everything here: **a silent session does not exist.** If it
fails, comes back empty or is cut off, the reason is in the channel. Otherwise a
failure reads as "there was nothing to report", which is the false clear we guard
against everywhere in this repo.

The posted TEXT is English (ADR-0001): it is the repo's own status text, not a
conversation with Mark.
"""
import re

# Fish a PR link out of the output. A writing session ends in a proposal, and
# that proposal is the only thing a human has to click.
PR_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")


def pull_request(text):
    """The LAST PR link in the output, or "". The last one, because a session may
    name one along the way as an example; the last is the one it opened."""
    found = PR_URL.findall(text or "")
    return found[-1] if found else ""


def footer(session, elapsed, result):
    """The stats line: how long, what it cost, how many turns — and for a writing
    session which branch, so you can find the work back even when no PR came out
    of it."""
    parts = [f"— session `{session['type']}` · {int(elapsed // 60)}m{int(elapsed % 60):02d}s",
             f"${float(result.get('total_cost_usd') or 0.0):.2f}",
             f"{int(result.get('num_turns') or 0)} turns"]
    if session.get("branch"):
        parts.append(f"branch `{session['branch']}`")
    return " · ".join(parts)


def result_text(session, elapsed):
    """Always something. A session that quietly yields nothing reads as 'nothing
    to report', and that is exactly what we do not want."""
    result = session.get("res") or {}
    answer = (result.get("result") or "").strip()
    foot = footer(session, elapsed, result)

    if not answer:
        return (f"⚠️ session `{session['type']}` ended without an answer "
                f"(exit {session['proc'].returncode}). Log: {session['path']}\n{foot}")
    if result.get("is_error"):
        answer = (f"⚠️ session got stuck ({result.get('subtype') or 'error'}):\n{answer}")

    pr = pull_request(answer)
    if session.get("writes"):
        # A writing session without a PR has not necessarily failed, but it is
        # the first thing you want to know.
        answer += (f"\n\n🔀 {pr}" if pr
                   else f"\n\n⚠️ no pull request in the output — work is in "
                        f"`{session.get('workdir', '?')}`")
    return f"{answer}\n\n{foot}"
