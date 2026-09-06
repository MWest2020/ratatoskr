# SPDX-License-Identifier: EUPL-1.2
"""Meldingen per beurt: statistiek naar #statistics, limitaties naar #escalatie.

Apart van listener.py zodat die onder de ≤200-regel-conventie blijft. `send` komt
als callable binnen (de listener bezit de buzz-omgeving en de sleutels); dit
bestand kent alleen het format en het beleid.
"""
import prompts


def report_run(send, channels, handle, cname, cfg, r):
    """Statistiek per beurt naar #statistics, en — alleen als er iets geweigerd is
    of misging — één geaggregeerde melding naar #escalatie (besluit Mark
    2026-09-06: per run, niet per geweigerde aanroep; mens beslist over verruiming).
    Melden mag nooit de beurt zelf laten klappen."""
    try:
        stats = channels.get("statistics")
        if stats:
            line = (f"{handle} · #{cname} · {r.get('model') or '?'} · "
                    f"{r.get('turns', 0)} turns · ${r.get('cost', 0.0):.2f}")
            send(stats, line, cfg["nsec"], cfg["npub"])

        denials, err = r.get("denials") or [], r.get("error") or ""
        # Zelfrapportage uit de tekst: zie prompts.LIMIT_CLAUSE.
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
        msg = (f"limitatie · {handle} in #{cname} · model {r.get('model') or '?'}\n"
               + (f"zelf gemeld: {limit}\n" if limit else "")
               + (f"geweigerd: {', '.join(tools)} ({len(denials)}x)\n" if denials else "")
               + (f"storing: {err}\n" if err else "")
               + "beslissen: rol verruimen in de handbook-def, of laten staan.")
        send(esc, msg, cfg["nsec"], cfg["npub"])
    except Exception as e:
        print(f"[listener] melden mislukt ({handle}): {e}", flush=True)
