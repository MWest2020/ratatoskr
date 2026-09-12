# SPDX-License-Identifier: EUPL-1.2
"""Push-melding bij een nieuw bericht.

De bestaande push-keten (orchestrator/push-notify.py → VAPID → telefoon) vuurde
alleen op run-verdicts en escalaties. Mark wil ook weten dát er iets in een kanaal
staat, zonder de app open te houden.

Wat NIET meldt: zijn eigen berichten (die schreef hij zelf), de ⋯-tussenstanden
(telemetrie, geen bericht) en #statistics (idem). Wat wél: een agent-antwoord of
een bericht van iemand anders.

Per kanaal hoogstens één push per COOLDOWN seconden; wat in die tijd binnenkomt
wordt geteld en gaat mee in de volgende ("+2 meer"). Anders trilt de telefoon bij
elke regel van een agent die net drie keer antwoordt.
"""
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = os.path.join(ROOT, "orchestrator", "push-notify.py")
COOLDOWN = int(os.environ.get("PUSH_COOLDOWN_SECONDS", "45"))
SILENT = ("statistics",)          # kanalen die nooit pushen
PROGRESS_PREFIX = "⋯"

_last: dict = {}                # kanaalnaam -> (tijdstip, onderdrukt aantal)


def should_notify(cname, author, content, me):
    """Is dit een bericht waar een mens iets aan heeft?"""
    if cname in SILENT:
        return False
    if author == me:                       # eigen bericht
        return False
    if (content or "").lstrip().startswith(PROGRESS_PREFIX):
        return False
    return bool((content or "").strip())


def push(cname, author, content):
    """Stuur één melding; faalt stil (een melding mag de listener nooit hinderen)."""
    now = time.time()
    t, missed = _last.get(cname, (0.0, 0))
    if now - t < COOLDOWN:
        _last[cname] = (t, missed + 1)     # binnen de cooldown: alleen tellen
        return False
    body = (content or "").strip().replace("\n", " ")
    if len(body) > 140:
        body = body[:137] + "…"
    if missed:
        body += f"  (+{missed} eerder)"
    _last[cname] = (now, 0)
    try:
        # Kanaal in de URL: een melding over #bouw hoorde je in #bouw te zetten,
        # niet op de app-root (= het eerste kanaal). Als HASH, want die gaat niet
        # naar de server en geeft dus geen tweede cache-entry in de sw.
        subprocess.run(["uv", "run", SENDER, "--title", f"#{cname} · {author}",
                        "--url", f"/#{cname}", "--body", body],
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
        return True
    except Exception as e:                 # sender weg, netwerk stuk, uv ontbreekt
        print(f"[listener] push mislukt (#{cname}): {e}", flush=True)
        return False
