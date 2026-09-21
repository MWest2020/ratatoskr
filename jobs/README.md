# jobs — recurring jobs (geplande claude -p-posts naar kanalen)

Geplande "nieuws"-jobs: op een tijdschema draait `claude -p` (sub-first) over
context van de host en post een digest naar een kanaal. Reboot-vast via
systemd user-timers (linger).

## Onderdelen
- `jobs.yml` — per job: kanaal-id, post-identiteit (handle), prompt, optioneel
  `context_cmd` (shell op de host; stdout = context voor claude -p).
- `run-job.py <naam>` — draait één job (context → claude -p → post).
- `run-jobs.sh <naam>` — SOPS-wrapper: exporteert NSEC_<HANDLE> en draait de job.
- systemd (agent-lxc, user): `ratatoskr-job@<naam>.service` (template) +
  per-job timer `ratatoskr-<kort>.timer`.

## Live jobs
- **news_from_zettelkast** (ma 09:00) — digest uit de zettelkast (journal +
  funding-memo), post als orchestrator.
- **proposals** (ma 09:15) — open OpenSpec-proposals uit het ecosysteem.
- **technical_debt** (vr 16:00) — architect reflecteert op technische schuld.
- **zettelkast_dagelijks** (dagelijks 09:00) — wat is er vandaag met Marks
  gedeelde clips gebeurd, wat staat er nog open. Draait ná de capture-run van de
  zettelkast (`zettelkast-daily.timer`, 06:00). De context splitst afgehandeld
  van open: een clip waarvan de fetch-snapshot al gecaptured is, is klaar — ook
  al citeert geen enkele wiki-pagina het clipbestand zelf.
- **standup** (dagelijks 08:00) — open werk (PR's/OpenSpec) + blokkades (#escalatie/#review).
- **gedaan** (dagelijks 18:00) — wat is er vandaag af (commits + gemergede PR's).

## Nieuwe job toevoegen
1. Kanaal aanmaken (web-app of `buzz channels create`), post-identiteit als lid.
2. Entry in `jobs.yml` (channel/identity/prompt/context_cmd).
3. Timer + template: `jobs/systemd/` bevat de gecommitte timers + het
   `ratatoskr-job@.service`-template; kopieer die naar `~/.config/systemd/user/`. Het template hoort gelijk te blijven
   aan de live host-unit (waar news/proposals/technical_debt op draaien); wijk je
   ervan af, werk beide bij.
4. `systemctl --user daemon-reload && systemctl --user enable --now ratatoskr-<x>.timer`.

Handmatig draaien/testen: `bash jobs/run-jobs.sh <naam>`.

## Timers

Alle timers staan in `jobs/systemd/` — óók de wekelijkse. Ze stonden tot
2026-09-11 alleen op de host, en dat is precies zo lang onzichtbaar als het
goed gaat. Installeren:

    cp jobs/systemd/ratatoskr-*.timer jobs/systemd/ratatoskr-job@.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    for t in standup gedaan zettelkast news proposals techdepth; do
      systemctl --user enable --now "ratatoskr-$t.timer"
    done

| timer | wanneer | job |
|---|---|---|
| standup | dagelijks 08:00 | standup |
| zettelkast | dagelijks 09:00 | zettelkast_dagelijks |
| gedaan | dagelijks 18:00 | gedaan |
| news | maandag 09:00 | news_from_zettelkast |
| proposals | maandag 09:15 | proposals |
| techdepth | vrijdag 16:00 | technical_debt |

## Een stille job bestaat niet

Levert een job geen digest op, dan post hij **in zijn eigen kanaal** waaróm
niet:

    ⚠️ job standup kon niet draaien: claude niet te starten (PermissionError: …)

Gedekt: `claude` niet te starten (`OSError`), een time-out, een niet-nul
returncode en een leeg antwoord. Het posten zelf kan die weg natuurlijk niet
gebruiken; dat blijft in het journaal staan.

Waarom dit er is: op 2026-09-21 sneuvelden om 08:00 alle vier de terugkerende
jobs tegelijk op een `claude`-installatie die er wél stond maar niet uitvoerbaar
was (de npm-postinstall had het platform-binary niet opgehaald). In de kanalen
stond niets. De storing kwam pas om 15:30 aan het licht doordat Mark vroeg "no
standup this morning?" — zeven uur later, en alleen omdat híj de afwezigheid
opmerkte.

Afwezigheid leest als "niets te melden", en dat is het gevaarlijke antwoord: een
lege #escalatie kan "geen blokkades" betekenen of "de job is dood", en van
buiten zien die er hetzelfde uit. Dezelfde regel als bij
[werksessies](../docs/how-to/werksessies.md).

Herstel van díe storing, voor als het terugkomt:

    node ~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/install.cjs
    # geeft dat de native package ontbreekt? dan de hele map opnieuw installeren:
    mv ~/.npm-global/lib/node_modules/@anthropic-ai/claude-code{,.kapot}
    npm install -g @anthropic-ai/claude-code && claude --version
