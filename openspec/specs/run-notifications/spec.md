# run-notifications Specification

## Purpose
TBD - created by archiving change add-notifications. Update Purpose after archive.
## Requirements
### Requirement: Posten gebeurt uitsluitend buiten de kooi

Posten naar de relay SHALL uitsluitend gebeuren door processen buiten de
habitat-kooi (orchestrator/dispatch op de orchestrator-host); worker-Jobs
SHALL geen relay-egress, geen buzz-sleutels en geen buzz-tooling krijgen.

#### Scenario: Kooi-diff is leeg

- **WHEN** deze change volledig is toegepast
- **THEN** is de diff op habitats `cage/`, `worker/` en NetworkPolicies leeg

### Requirement: Run-lifecycle in #runs

Per dispatch SHALL de start (rol, change, repo, run-id) en het einde (verdict,
kosten, branch, link naar het run-rapport) gepost worden in `#runs`, in één
thread per run.

#### Scenario: Groene run

- **WHEN** een builder-run slaagt
- **THEN** bevat de thread het PASS-verdict, de branchnaam en de rapportlink

### Requirement: Best-effort — de relay blokkeert nooit een run

Notificeren SHALL best-effort zijn: een onbereikbare relay of falende post
SHALL een dispatch of run nooit vertragen, blokkeren of laten falen; een
gemiste notificatie SHALL zichtbaar zijn in het lokale log.

#### Scenario: Relay plat tijdens een run

- **WHEN** de relay onbereikbaar is terwijl een run eindigt
- **THEN** rondt de run normaal af (verdict via git/exit-code zoals altijd) en
  logt de orchestrator de gemiste post

### Requirement: Berichten zijn spiegel en bevatten geen geheimen

Berichten SHALL alleen metadata en links bevatten — nooit PAT's, sleutels,
diff-inhoud van privérepo's of andere geheimen — en SHALL nooit de
gezaghebbende bron zijn: bij tegenspraak wint git + audit-JSONL.

#### Scenario: Tegenspraak

- **WHEN** een bericht en het audit-spoor in git elkaar tegenspreken
- **THEN** geldt git en wordt het bericht gecorrigeerd, nooit andersom

### Requirement: Uitkomsten naar het passende kanaal

De ping-helper SHALL een bericht naar een gekozen kanaal kunnen sturen (niet alleen
#general), zodat uitkomsten in het juiste kanaal landen — review-verdicts in
#review, build-run-uitkomsten in #runs.

#### Scenario: Review-verdict naar #review

- **WHEN** een review-uitkomst wordt gepost via de ping-helper met kanaal `review`
- **THEN** verschijnt het verdict in #review (ondertekend door de reviewer-identiteit),
  niet in #general

### Requirement: Telefoon-push bij verdict en escalatie

Naast de post in `#runs`/`#escalatie` SHALL `buzz-notify.sh` bij een run-einde
(verdict) en bij een escalatie een Web Push naar de geregistreerde apparaten
afvuren, zodat Mark de melding ook op de telefoon krijgt met de app gesloten.
Dit SHALL opt-in zijn via `BUZZ_PUSH=1` en SHALL de bestaande best-effort-garantie
erven: een ontbrekende sender, lege uv-cache of onbereikbare push-service SHALL een
run nooit vertragen of laten falen (de aanroep is achtergrond + getimed, fouten
gaan naar `notify.log`). De push SHALL alleen metadata bevatten (verdict, change,
branch, reden) — nooit geheimen — conform de bestaande spiegel-eis.

#### Scenario: Verdict met push aan

- **WHEN** een run eindigt terwijl `BUZZ_PUSH=1` en er ten minste één apparaat is
  aangemeld
- **THEN** verschijnt het verdict zowel als bericht in `#runs` als als push-melding
  op het toestel, en blokkeert het versturen de afronding van de run niet

#### Scenario: Push-pad kapot, run ongemoeid

- **WHEN** de sender ontbreekt of de push-service onbereikbaar is bij een run-einde
- **THEN** rondt de run normaal af, staat de `#runs`-post er gewoon, en logt de
  orchestrator de gemiste push zonder de run te vertragen of te laten falen

