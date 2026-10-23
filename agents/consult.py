# SPDX-License-Identifier: MIT
"""The hub consults other agents: `!consult <agent>[,<agent>] <question>`.

Mark, 2026-10-23: "ja, bouw !consult". On 2026-10-23 odin had to ask Mark to
post its questions to @architect and @reviewer himself. Its `!route` posts a
message under odin's own key, and the listener skips agent messages (the loop
guard), so a forwarded question was never answered. Consulting is the road
odin was missing: the listener gives the named agents a turn itself, in the
channel where Mark asked, and each answers under its own name.

Limits, enforced here and not in a prompt:

- only the hub's own answer, FIRST line (a quote further down never acts);
- at most MAX agents per answer, existing ones, not the hub itself;
- a consulted agent's answer is never read for `!consult`, so no chains;
- once they have answered, the hub gets ONE follow-up turn with their answers
  (2026-10-23: odin wrote "then I open the issues and !propose" after its
  consult, and nothing ever woke it to do so). That turn cannot consult or
  start a session, so it ends there.
"""
import re

MAX = 2
MARKER = re.compile(r"^!consult\s+([a-z][a-z0-9_-]*(?:,[a-z][a-z0-9_-]*)*)\s+(\S.*)$")


def read_marker(answer):
    """(agents, question) from the first line of the answer, or None."""
    first = (answer or "").strip().split("\n", 1)[0].strip()
    m = MARKER.match(first)
    if not m:
        return None
    names = list(dict.fromkeys(m.group(1).split(",")))
    return names, m.group(2).strip()


def strip_marker(text):
    lines = (text or "").strip().split("\n", 1)
    if lines and MARKER.match(lines[0].strip()):
        return lines[1].strip() if len(lines) > 1 else ""
    return text


def plan(names, hub, agents, may_speak):
    """(who is consulted, why the others are not)."""
    take, refused = [], []
    for n in names:
        if n == hub or n not in agents:
            refused.append(f"{n} is not an agent to consult")
        elif not may_speak(n):
            refused.append(f"{n} cannot speak in this channel")
        elif len(take) >= MAX:
            refused.append(f"{n}: at most {MAX} agents per answer")
        else:
            take.append(n)
    return take, refused


def prompt_for(question, human_message, hub):
    """What the consulted agent gets as the message to answer."""
    return (f"{hub} consults you on Mark's message. Answer the question for your part, "
            f"as your contract says; you cannot consult others yourself.\n\n"
            f"{hub}'s question: {question}\n\nMark's message:\n{human_message}")


def followup_for(answers, human_message):
    """The hub's prompt once the consulted agents have answered."""
    return ("The agents you consulted have answered:\n\n" + "\n\n".join(answers)
            + "\n\nAct on it now: take the next step you announced (an issue, "
            "`!propose`, `!build`), or tell Mark in one message what blocks it. "
            "You cannot consult again or start a session from this turn.\n\n"
            f"Mark's message, for reference:\n{human_message}")


def clause(handle, hub):
    if handle != hub:
        return ""
    return ("\n\nYou can CONSULT other agents yourself: put `!consult <agent>[,<agent>] "
            "<question>` on the FIRST line of your answer (at most two). The listener "
            "gives each of them a turn in this channel with Mark's message and your "
            "question, and they answer here under their own name. Use it instead of "
            "asking Mark to post a question in another channel.")
