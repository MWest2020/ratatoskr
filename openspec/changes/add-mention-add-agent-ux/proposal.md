# Change: add-mention-add-agent-ux

## Why

@mention naar een agent die niet in het kanaal zit gaf een kale relay-error (en de
vorige workaround — een geforceerde `--mention` met een vaste pubkey — brak zodra
die pubkey zelf geen lid van het kanaal was, bv. #red-team). Mark wil i.p.v. een
error een pop-up "agent zit niet in dit kanaal — toevoegen?".

## What Changes

- **Send zonder geforceerde `--mention`**: de relay resolvet een @agent naar het lid
  en triggert 'm; een @naam die geen lid is geeft een nette fout die de naam noemt.
- **`/api/send`** vangt die fout op en antwoordt gestructureerd
  (`409 {missing_agent, known, channel}`) i.p.v. een 502.
- **`/api/channel/add-member`** (nieuw): voegt een agent (naam→pubkey uit de
  registry) toe aan het kanaal.
- **Frontend**: bij `missing_agent` een pop-up "@X zit niet in #kanaal — toevoegen?";
  na toevoegen wordt het bericht automatisch opnieuw verstuurd. Onbekende naam →
  nette melding.
- **Nieuw kanaal krijgt coordinator standaard** (beleid: coordinator in elk kanaal):
  `/api/channels/create` voegt 'm best-effort toe na aanmaken.
- Verwijdert de `MENTION_PUBKEY`-workaround (was niet overal lid).

## Impact

- `chat/server.py` (send-flow + add-member-route), `chat/roster.py` (`pubkey_of`),
  `chat/buzzcli.py` (MENTION_PUBKEY weg), `chat/app.js` (pop-up + retry), `chat/app.css`.
  Read/write, additief; live gesmoked (ok / 409 / add / retry / 404).
