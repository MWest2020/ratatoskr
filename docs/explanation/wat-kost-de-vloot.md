---
status: current
last_reviewed: 2026-09-21
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

## Als de hele digest ontbreekt

Dat is iets anders dan een ontbrekende statistiekregel, en het is ernstiger.
Sinds 2026-09-21 post een job die niets kan opleveren een regel in **zijn eigen
kanaal**:

    ⚠️ job standup kon niet draaien: claude niet te starten (PermissionError: …)

Gedekt: `claude` niet te starten, een time-out, een niet-nul returncode, een
leeg antwoord. Het posten zelf kan die weg niet gebruiken — mislukt dát, dan
staat het alleen in het journaal.

Aanleiding: op 2026-09-21 om 08:00 sneuvelden alle vier de terugkerende jobs
tegelijk op een `claude` die er wél stond maar niet uitvoerbaar was. In de
kanalen stond niets, en de storing kwam pas om 15:30 aan het licht doordat Mark
vroeg "no standup this morning?".

De oorzaak van díe storing was de auto-updater van Claude Code, die zichzelf elke
kwartier bijwerkte en een keer een installatie zonder werkende binary achterliet.
Hij staat nu uit; bijwerken is een bewuste handeling geworden. Het hele verhaal
en het herstelrecept staan in `jobs/README.md`.

Zonder zo'n regel valt een dode job niet te onderscheiden van een rustige dag:
een lege #escalatie kan "geen blokkades" betekenen of "de job draait al zeven
uur niet meer". Dezelfde regel als bij [werksessies](../how-to/werksessies.md):
afwezigheid is geen bericht. Het herstelrecept voor dit specifieke geval staat
in `jobs/README.md`.
