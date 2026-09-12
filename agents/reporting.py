# SPDX-License-Identifier: EUPL-1.2
"""Reports per turn: statistics to #statistics, limitations to #escalatie.

Separate from listener.py so that file stays under the ≤200-line convention.
`send` comes in as a callable (the listener owns the buzz environment and the
keys); this file knows only the format and the policy.

The reported TEXT stays Dutch: it lands in the Dutch channels.
"""
import time

import prompts
import providers
import topology

# How many progress lines per turn, and the minimum seconds between them.
PROGRESS_MAX = 4
PROGRESS_GAP = 20



def progress_poster(send, cid, cfg, handle):
    """Returns a callback that shows WHAT the agent is doing along the way.

    Why: a turn takes up to 150s and until now that was pure silence — Mark saw
    nothing until the answer arrived. The first step goes out immediately, then at
    most one line every PROGRESS_GAP seconds, with a hard ceiling. Reporting must
    never slow the turn down or make it fail, so everything sits in a try.
    """
    state = {"n": 0, "t": 0.0}

    def progress(what):
        now = time.time()
        if state["n"] >= PROGRESS_MAX:
            return
        if state["n"] and now - state["t"] < PROGRESS_GAP:
            return
        state["n"] += 1
        state["t"] = now
        try:
            send(cid, f"⋯ {handle}: {what}", cfg["nsec"], cfg["npub"])
        except Exception:
            pass

    return progress


def report_run(send, channels, handle, cname, cfg, r):
    """Statistics per turn to #statistics, and — only when something was refused
    or went wrong — one aggregated report to #escalatie (Mark, 2026-09-06: per
    run, not per refused call; a human decides about widening). Reporting must
    never make the turn itself fail."""
    try:
        stats = channels.get("statistics")
        if stats:
            requested, actual = r.get("model_requested") or "", r.get("model") or "?"
            # Requested AND actual, with a flag when they differ: this line is
            # the only place Mark can read whether the declared model is really
            # enforced. Showing only "what ran" hides exactly that.
            model = actual if not requested else (
                f"{requested}→{actual}" + ("" if providers.model_matches(requested, actual)
                                            else "  ⚠ WIJKT AF"))
            line = (f"{handle} · #{cname} · {model} · "
                    f"{r.get('turns', 0)} turns · ${r.get('cost', 0.0):.2f}")
            send(stats, line, cfg["nsec"], cfg["npub"])

        denials, err = r.get("denials") or [], r.get("error") or ""
        # Self-reporting from the text: see prompts.LIMIT_CLAUSE.
        limit = next((ln.split(":", 1)[1].strip()
                      for ln in (r.get("answer") or "").splitlines()
                      if ln.strip().startswith(prompts.LIMIT_MARKER)), "")
        if not denials and not err and not limit:
            return
        esc = channels.get("escalatie")
        if not esc:
            print(f"[listener] {handle}: limitatie maar #escalatie onbekend: "
                  f"{len(denials)} denial(s) {err}", flush=True)
            return
        tools = sorted({d.get("tool_name") or d.get("tool") or "?" for d in denials
                        if isinstance(d, dict)})
        # The advice follows the CAUSE. This used to always say "widen the role",
        # even on a timeout — and then the report points at a button that fixes
        # nothing.
        if denials or limit:
            advice = ("beslissen: rol verruimen in de handbook-def "
                      f"({', '.join(tools) if tools else 'de gemelde tool'}), of laten staan.")
        elif err == "timeout":
            advice = (f"beslissen: de vraag was te groot voor één beurt "
                      f"({providers.MAX_TURN_S}s). Opknippen, of als dit vaker gebeurt "
                      f"het zware werk als habitat-run doen — dat heeft 30 minuten.")
        else:
            advice = "beslissen: storing bekijken in het listener-log; geen rolkwestie."
        msg = (f"limitatie · {handle} in #{cname} · model {r.get('model') or '?'}\n"
               + (f"zelf gemeld: {limit}\n" if limit else "")
               + (f"geweigerd: {', '.join(tools)} ({len(denials)}x)\n" if denials else "")
               + (f"storing: {err}\n" if err else "")
               + advice)
        send(esc, msg, cfg["nsec"], cfg["npub"])
    except Exception as e:
        print(f"[listener] melden mislukt ({handle}): {e}", flush=True)


def report_missing_memberships(run, agents, channels, pub2name):
    """Report at start-up which agent memberships are missing. No exit: an agent
    that is not in #statistics must still answer. Loudly though, because otherwise
    the send only fails in the log — observed 2026-09-07, when the escalation
    chain was dead in practice for five of the eight agents."""
    name2pub = {h: p for p, h in pub2name.items()}
    missing = topology.missing_memberships(
        agents, channels, name2pub, lambda cid: topology.members(run, cid))
    for handle, cname in missing:
        print(f"[listener] LIDMAATSCHAP ONTBREEKT: @{handle} post in #{cname} maar is "
              f"geen lid — die send zal falen (bash ~/bh/members.sh --yes)", flush=True)
    return missing
