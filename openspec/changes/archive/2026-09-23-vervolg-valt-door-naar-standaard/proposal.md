# Een agent die hier niet mag vervolgen, geeft de beurt aan de standaard

## Why

Na `default-agent-per-channel` bleef er één geval stil. In `#general` wordt
architect met `@architect` aangeroepen; dat mag via relay-lidmaatschap. Zegt
een mens daarna iets zonder handle, dan is architect de meest recente agent,
maar hij mag in `#general` niet vervolgen. `triggers.pick` stopte dan met
`[]`: niemand antwoordde, ook de standaard-agent niet.

`design.md` van de vorige change noemt precies dat de faalvorm die deze repo
al elders betaalt: stilte die niet te onderscheiden is van een kapotte
listener. Mark, 2026-09-23: val door naar de standaard.

## What changes

In `agents/triggers.py` wordt de vroege `return [], ""` een `break`: het
bericht telt als koude start. Zonder standaard-agent in dat kanaal verandert
er niets — dan blijft het stil, zoals elke koude start daar.

## Not changing

Alleen de meest recente agent telt nog steeds. Verder terug zoeken naar een
agent die wél mag vervolgen blijft verboden; zo wordt een agent wakker op
andermans draad.
