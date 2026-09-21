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
jobs tegelijk op een `claude` die er wél stond maar niet uitvoerbaar was. In de
kanalen stond niets. De storing kwam pas om 15:30 aan het licht doordat Mark
vroeg "no standup this morning?" — zeven uur later, en alleen omdat híj de
afwezigheid opmerkte. De oorzaak staat hieronder.

Afwezigheid leest als "niets te melden", en dat is het gevaarlijke antwoord: een
lege #escalatie kan "geen blokkades" betekenen of "de job is dood", en van
buiten zien die er hetzelfde uit. Dezelfde regel als bij
[werksessies](../docs/how-to/werksessies.md).

## De storing van 2026-09-21: de auto-updater

Wat het startte was niet een mens en geen cron, maar **de auto-updater van
Claude Code zelf**. Elke ~15 minuten draaide hij twee commando's:

    npm view @anthropic-ai/claude-code@latest version --prefer-online
    npm install --global @anthropic-ai/claude-code@<nieuwste>

`npm install -g` is niet atomair: hij hernoemt de bestaande installatie eerst
opzij. Om 07:16 lukte dat — de werkende boom belandde in
`@anthropic-ai/.claude-code-<random>` — en de nieuwe installatie leverde om 07:26
alleen een **stub van 500 bytes** af:

    Error: claude native binary not installed.
    Either postinstall did not run (--ignore-scripts, some pnpm configs)
    or the platform-native optional dependency was not downloaded (--omit=optional).

Het platform-pakket `@anthropic-ai/claude-code-linux-x64` was niet meegekomen.
Dat is een **optionele** dependency, en npm laat een installatie slagen als een
optionele dependency ontbreekt. Een geslaagde update zonder werkende binary dus.
De stub stond bovendien op `rw-rw-r--`, dus het viel al om bij het starten:

    PermissionError: [Errno 13] Permission denied: '/home/agent/.npm-global/bin/claude'

Niet de oorzaak, nagekeken: `~/.npmrc` bevat alleen `prefix=`, `npm config get
omit` is leeg en `ignore-scripts` staat op `false`. Er is geen configuratie die
optionele pakketten overslaat; het was een mislukte ophaalactie die als succes
werd geteld.

Daarna bleef het hangen: elke volgende poging botste op die 224 MB rest met
`ENOTEMPTY: directory not empty, rename …`. Toevallig beschermend — de updater
kón de herstelde installatie niet meer aanraken — maar toeval is geen maatregel.

### Wat er nu tegen staat

De updater staat **uit**, in `~/.claude/settings.json`:

```json
{ "autoUpdates": false, "env": { "DISABLE_AUTOUPDATER": "1" } }
```

Beide namen zitten in de gebruikte build (opgezocht in het binary, niet gegokt).
Let op: dit geldt voor sessies die daarná starten — een langlopende sessie houdt
zijn eigen gedrag tot hij herstart.

Bijwerken is daarmee een **bewuste handeling** geworden, en die hoort altijd zo
te eindigen:

    npm install -g @anthropic-ai/claude-code
    claude --version          # moet een versie tonen, geen foutmelding
    ls -l ~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/bin/
    # claude.exe hoort honderden MB's te zijn en uitvoerbaar (rwx).
    # Is het een bestand van ~500 bytes, dan is het de stub: niet goed.

In `~/opt/claude-code-2.1.197-terugval` staat een bewezen werkende boom als
terugval. Terugzetten:

    D=~/.npm-global/lib/node_modules/@anthropic-ai
    mv $D/claude-code $D/claude-code.kapot
    cp -a ~/opt/claude-code-2.1.197-terugval $D/claude-code
    claude --version

### Herstel als het tóch weer gebeurt

    # 1. staat er een stub?
    ls -l ~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/bin/
    # 2. staat de vorige installatie nog als rest? die is meestal compleet:
    ls -d ~/.npm-global/lib/node_modules/@anthropic-ai/.claude-code-*
    # 3. anders opnieuw installeren -- eerst de map opzij, anders ENOTEMPTY:
    D=~/.npm-global/lib/node_modules/@anthropic-ai
    mv $D/claude-code $D/claude-code.kapot
    npm install -g @anthropic-ai/claude-code && claude --version

En daarna: `systemctl --user reset-failed 'ratatoskr-job@*'`, en de gemiste jobs
met de hand inhalen (`systemctl --user start ratatoskr-job@<naam>.service`).
