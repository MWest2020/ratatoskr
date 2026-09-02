## Why

Alle vaste Claude-sessies postten in #general onder de identiteit **'bouwer'** met
een `[naam]`-tekst-prefix (workaround). Dat botst met het kernprincipe van de
identity-registry — *"identiteit = sleutelpaar, geen accountnaam"*: berichten zijn
niet aan de echte afzender toe te schrijven en het **audit-spoor zegt 'bouwer'**
terwijl bouwer niet de afzender was.

## What Changes

- **`orchestrator/create-session-identity.py`**: een LICHT identiteit-mechanisme —
  keypair + `identities.yml`-entry (rol `sessie`) + SOPS-nsec + relay-lid +
  #general-lid + profielnaam. **Geen** handbook-def en **geen** listener-run-lijst
  (een sessie is een interactieve Claude-sessie, geen door de listener gespawnde
  chat-agent — dat onderscheid is bewust).
- **`ping.sh` krijgt een `IDENT`-parameter** (default `bouwer` voor compat); een
  sessie post nu onder eigen sleutel: `IDENT=hubby ping.sh '...'`.
- **Vier sessie-identiteiten aangemaakt**: hubby, versum, hub, internetnl-cli.
- **Niet gedaan (bewust):** het tailnet-adres als relay-URL. De relay is
  community-scoped op de LAN-host (`192.168.178.60`); via het tailnet-IP komt
  "no community configured for this host". Een echte tailnet-relay vergt een
  relay-herconfig — aparte taak, buiten deze change. ping.sh houdt de LAN-host
  (werkt vanaf tailnet-nodes via de subnet-router).
