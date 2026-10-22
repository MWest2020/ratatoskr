# orchestrator

De weg van chat naar habitat is `!build <repo> <openspec-change>
[issue-nummer]`, gecheckt door de listener (`agents/build.py`); zie
`docs/how-to/build-from-chat.md`. `orchestrator/bridge.py` (het
`!dispatch`-poortwachtermodel uit `add-habitat-bridge`) is nooit uitgerold en
is verwijderd (change `retire-bridge`).

## add-member.py — pubkey als kanaallid

    python3 orchestrator/add-member.py --chan escalatie --name odin-worker

Lost kanaal en identiteit op uit `channels.yml` / `identities.yml`, zodat er geen
UUID of pubkey op de commandline hoeft (die breken in een terminal over meerdere
regels en falen dan stil-verkeerd). `--all-channels` voegt in één keer overal toe,
idempotent — "al lid" is geen fout.

Tekent standaard als **orchestrator**, conform `reown-channels-to-orchestrator`.
Is een kanaal nog mens-owned, dan `IDENT=mark` ervoor tot `reown-channels.py`
gedraaid heeft.

## push-notify.py — een melding naar de telefoon

    uv run orchestrator/push-notify.py --title "PR #7" --body "verdict: FAIL" --url /

Leest de abonnementen van de VM via de gepinde helper (`boomhuis-push-subs read`)
en verstuurt met de VAPID-sleutel uit SOPS. Zonder abonnees zegt hij dat en stopt.

**De verzendkant testen zonder telefoon:**

    cd orchestrator && uv run --with pywebpush --with pyyaml --with cryptography \
      --with http-ece python -m unittest test_push_send -v

Die test speelt zelf voor pushdienst: hij maakt een abonnement zoals een browser
dat doet, vangt de POST op localhost en ontsleutelt de inhoud. Hij bewijst alles
wat aan ónze kant fout kan gaan — SOPS, de JWT-ondertekening, de versleuteling,
en de `Urgency`/`TTL`-headers die bepalen wánneer een toestel de melding ziet.
Slaat zichzelf over als SOPS of de age-sleutel ontbreekt, want `verify.sh` moet
offline groen zijn; hij draait dus alleen als je hem expliciet zo aanroept.

Blijft er daarna nog "geen meldingen" over, dan zit het in de browser-permissie
op het toestel — zie `chat/app-push.js` en `chat/e2e/push-states.js`.
