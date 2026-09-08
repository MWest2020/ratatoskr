# Change: enforce-model-and-tools

## Why

De handbook-definities kregen model en tools (`add-model-and-real-tools`), maar de
listener gaf ze niet mee: `claude -p --append-system-prompt <system> <prompt>`,
zonder `--model` en zonder `--allowedTools`. Gedeclareerd is niet afgedwongen.
Mark, 2026-09-06: *"afdwingen. ik wil dus horen van de coordinator wanneer we
limitaties hebben. dan human in de loop en beslissen. niet yolo free for all."*

## What changes

- **`providers.run`** geeft `--model`, `--allowedTools` en `--disallowedTools` mee
  en draait met `--output-format json`, zodat gedraaid model, turns, kosten,
  `permission_denials` en fouten terugkomen in plaats van alleen tekst.
- **`bootstrap.build_agents`** (verplaatst uit listener.py) leest `model`, `tools`
  en `skills` uit de definitie en spawnt **niet** zonder model — vierde
  fail-closed-check naast nsec, def en npub.
- **`reporting.report_run`**: één statistiekregel per beurt naar `#statistics`,
  en bij een grens één geaggregeerde melding naar `#escalatie`.
- **`#statistics`** aangemaakt op de relay en geregistreerd in `channels.yml`.

## De vondst die het ontwerp veranderde

`permission_denials` blijft **leeg** bij een geweigerde tool: met een allowlist
wordt die tool niet eens aangeboden, dus er is geen aanroep om te weigeren. Live
geverifieerd — het bestand werd niet gemaakt en de agent antwoordde "de Write-tool
is uitgeschakeld voor deze sessie", terwijl `permission_denials: []` bleef.

Alleen op dat veld leunen zou dus een escalatiekanaal opleveren dat nooit
afgaat. Daarom vraagt de listener elke agent om één machineleesbare regel
(`LIMITATIE: …`) wanneer hij iets niet kan; die tilt hij naar `#escalatie`.
`permission_denials` blijft óók gelezen — dat vult zich wél in de kooi, waar
allow-regels op patroon staan (`Bash(git add *)`).

## Bug die de test ving

`--allowedTools`/`--disallowedTools` zijn variadisch (`<tools...>`): een prompt
als laatste argument werd erdoor opgeslokt, met "Input must be provided either
through stdin or as a prompt argument" tot gevolg. De prompt gaat nu via **stdin**.
Zonder die test was elke beurt stilgevallen zodra tools werden meegegeven.

## Impact

- `listener.py` blijft onder de 200-regelgrens (190) doordat agent-opbouw naar
  `bootstrap.py` ging en melden naar het nieuwe `reporting.py` (38 regels).
- Zonder de handbook-PR (#12) heeft geen enkele def een `model` en spawnt de
  listener **niets**. Die moet dus eerst gemerged; anders valt de vloot stil.
