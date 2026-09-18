---
status: current
last_reviewed: 2026-09-18
---

# Wat kost de vloot — en waar je dat leest

`#statistics` heeft één taak: per beurt één regel met wie er draaide, in welk
kanaal, op welk model, hoeveel beurten en wat het kostte. Niet om mooi te zijn,
maar zodat het bedrag niet pas op de rekening zichtbaar wordt.

    orchestrator · job standup · claude-sonnet-5 · 1 turns · $0.09
    bouwer · #bouw · sonnet→claude-sonnet-5 · 1 turns · $0.15

De pijl staat er met opzet: links wat er *gevraagd* is, rechts wat er *draaide*.
Lopen ze uiteen, dan staat er `⚠ DIFFERS` achter. Dat is de enige plek waar te
lezen valt of het gedeclareerde model ook echt afgedwongen wordt.

## Wie er een regel post

| loopt | post een regel | waar staat dat |
| --- | --- | --- |
| beurt van een chat-agent | ja | `agents/reporting.py` |
| terugkerende job (standup, digest, …) | ja | `jobs/run-job.py` |
| werksessie (`!sessie`) | in het eigen kanaal, niet hier | `agents/session_report.py` |
| habitat-run | in `#runs`, met verdict | `notify/buzz-notify.sh` |

Tot 18-09-2026 postten alleen de chat-agents. De terugkerende jobs draaien elke
dag `claude -p` en kosten geld, maar kwamen er nooit in voor — waardoor het
kanaal eruitzag alsof het willekeurig meldde. Gemeten over vier dagen: tien
agent-beurten, tien regels, geen enkel gat; de zes dagelijkse jobs: nul regels.

## Waarom je er geen melding van krijgt

`#statistics` is uitgezonderd van de push-meldingen (`SILENT` in
`agents/notify.py`). Het is een feed om terug te lezen, geen bericht dat je moet
weten. Zie [meldingen aanzetten](../how-to/pwa-installeren.md).

## Als een regel ontbreekt

De statistiekregel is nadrukkelijk *best-effort*: hij gaat pas uit nadat de
digest zelf geplaatst is, en een mislukking wordt gelogd maar laat de job staan.
Een job is er voor de digest. Levert de CLI onverwacht geen JSON meer, dan
verdwijnt de statistiekregel en blijft de digest gewoon komen — die volgorde is
een keuze, geen toeval.
