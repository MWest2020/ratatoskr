---
type: handover-baton
van: security-review-sessie + boomhuis (tweede, onafhankelijke blik)
naar: Mark
status: afgehandeld (op ontwerp-beslispunten na)
onderwerp: geautoriseerde security-pass wordsworth-PII-pad + boomhuis-comms
datum: 2026-08-30
scope: MWest2020/wordsworth (homelab) + boomhuis chat-backend. Alma (prod) OUT-OF-SCOPE.
autorisatie: Marks eigen infra/repo's; read/gerichte probes, geen DoS/destructief.
artefact_links:
  - wordsworth-console (live): https://mwest2020.github.io/wordsworth-console/  # commit f15571d
  - wordsworth F1/F3-mitigaties: MWest2020/wordsworth (auth per-caller keys + grant-scoping)
next_step: RONDE COMPLEET (2026-08-31); F3 STRUCTUREEL GEFIXT + gedeployed (2026-09-04, wordsworth PR #35 + homelab 57dafaf). Rest = alleen F2 als staande guardrail (nooit VC REQUIRED met test/publieke issuer). Nog open: optionele app-token op comms (niet nodig zolang elke tailnet-node Marks eigen hardware is) en de reboot-test van de relay-VM (Mark, wanneer het uitkomt).
---

# Verdict — security-pass wordsworth-PII-pad + boomhuis-comms (2026-08-30)

Twee sessies, wederzijds geverifieerd: de review-sessie vond en mitigeerde, de
boomhuis-sessie deed de onafhankelijke tweede blik + verifieerde elke finding
tegen een reproduceerbaar exploit-pad. Alleen findings mét repro + geverifieerde
fix. Privaat vastgelegd (boomhuis is privé); wordsworth is een PUBLIEKE repo, dus
exploit-details horen hier, niet daar.

## Findings

### F1 — gedeelde api-key ⇒ geen toerekenbaarheid · Medium · FIXED+verified
- **Entry:** `X-API-Key` → caller-label (auth.py); reveal legt `request.state.caller`
  vast in het hash-chained audit (api.py:531).
- **Defect:** één `label:key`-paar (`test:<key>`) ⇒ elke caller = `test` ⇒ geen
  non-repudiation in het append-only audit (kern-invariant).
- **Fix (peer):** secret nu additief `test`/`console`/`cli` (geen lockout).
- **Bewijs:** reveal met console-key → audit `caller=console` (distinct); wrong
  key → 401. Non-repudiation hersteld.

### F3 — ongescopete grants reveal op álle docs · Low/Med · STRUCTUREEL GEFIXT (2026-09-04)
- **Entry:** `POST /documents/{id}/reveal` met een global grant.
- **Defect:** `grants.py:39` markeert `document_id=None` als "global"; `authorize()`
  (r.67) slaat de doc-check over als `document_id is None` ⇒ één grant reveal-t op
  elk document. Live-repro: één `[PERSON]`-grant → 200 op twee doc-id's.
- **Eerste fix (peer, 2026-08-30):** Console geeft nu optioneel `document_id` mee
  (scoping). Bewijs: gescopete grant → reveal op eigen doc 200, op ander doc 403.
- **Waarom dat niet genoeg was:** die fix zat bij de *uitgever*. Het console-veld
  heet "document-id (optioneel)" en `authorize()` zag `document_id is None` nog
  steeds als global — een grant die je leeg laat, of die rechtstreeks in de DB
  staat, reveal-t nog steeds alles. Veilig pad mogelijk, niet default.
- **Structurele fix (2026-09-04, wordsworth PR #35, change `harden-global-grant-gate`):**
  `WORDSWORTH_ALLOW_GLOBAL_GRANTS`, default `false`. Ongescopete grant wordt
  geweigerd bij issue (400, geen grant-rij, geen audit-event) **en** is inert in
  `authorize()`, dus ook grants van vóór de gate vallen eronder. Spec-amendement
  op de `grants`-capability door Mark geratificeerd; bewust breaking-by-default,
  wat kon omdat er live 6 ongescopete grants zijn en daarvan **0 actief**.
  Volgt het precedent van `add-domain-keys` ("a grant never spans domains
  implicitly").
- **Live bewijs (homelab, image `sha-33186cb`, gate DICHT):** issue zonder
  `document_id` → 400 met detail; mét `document_id` → 201; reveal op eigen
  document → 200 (`['EMAIL']`); reveal op een ánder document → 403
  "grant not applicable"; smoke-grant daarna ingetrokken. De API-key is binnen
  de pod gebruikt, dus geen sleutelmateriaal in transcript of logs.
- **Bijvangst van deze deploy:** de ArgoCD PreSync-init-job stond gepind op
  `sha-06f7294` en had de kolom-migraties uit `init_schema()` nooit toegepast
  (`grants.domain`, `pii_mappings.norm_version` ontbraken). Zichtbaar als 500 bij
  elke grant-issue zodra de api op een post-#34-image kwam. Opgelost door
  init-job en api op dezelfde sha te pinnen (homelab `57dafaf`); init draaide
  daarna "schema ready" en beide kolommen bestaan. **Les: init-job en api altijd
  samen bumpen.**

### Comms — chat-backend bindt 0.0.0.0, geen auth, tekent als mark · Medium · FIXED+verified
- **Entry:** `POST http://192.168.178.60:8090/api/send` (ook `/api/channels/create|delete`).
- **Defect:** `chat/server.py` bond op `("0.0.0.0", 8090)` zonder auth en tekende
  elk bericht als `mark`. Bereikt vanaf een andere host over de LAN. Elke node op
  het homelab-net (incl. andere agents) kon als mark posten / kanalen CRUD-en.
- **Correctie op de eerste fix-formulering:** tailscale draaide NIET op de VM
  (enige interface eth0 192.168.178.60; geen 100.x). "Tailnet-only" kwam van een
  subnet-router elders. Binden op 192.168.178.60 zou de LAN-exposure niet sluiten.
- **Gekozen fix (Mark, 2026-08-30): optie 2 — tailscale op de VM + socket-bind op
  het echte 100.x.** Uitgevoerd: tailscale geïnstalleerd op de relay-VM (join via
  1-daagse auth-key), VM-tailnet-IP = `100.80.218.83` (`boomhuis-relay`).
  `chat/server.py` nu `BIND_HOST`-configureerbaar (default 0.0.0.0); op de VM
  `BIND_HOST=100.80.218.83` in `chat.env`. Systemd drop-in `10-wait-tailnet.conf`
  wacht op het tailnet-IP vóór de bind (reboot-race) + `Restart=on-failure`.
- **Re-test (vanaf agent-lxc, tailnet-node 100.90.159.10):** ná de flip →
  `tailnet 100.80.218.83:8090` = 200, `LAN 192.168.178.60:8090` = connection
  refused (was 200). Impersonatie vanaf het LAN is dicht.
- **Verder gehard (PWA-fase):** backend nu op loopback `127.0.0.1:8090`, naar buiten
  via `tailscale serve` met HTTPS op `https://boomhuis-relay.tail8f7877.ts.net`.
  Geen directe :8090-poort meer op LAN of tailnet-IP (beide geverifieerd dicht);
  toegang loopt uitsluitend via de tailnet-HTTPS-proxy. Nieuwe URL vervangt de
  oude LAN-URL.
- **Nog open (optioneel):** app-token op de write-endpoints als tweede laag
  (defense-in-depth). Nu niet nodig — netwerklaag is dicht; alleen als een
  tailnet-node ooit gecompromitteerd raakt. Marks keuze.
- **Niet live-reboot-getest:** de relay-VM niet herstart (verstoort de dienst);
  resilience is by-design (drop-in + Restart). Mark kan reboot-testen wanneer 't uitkomt.

## Beslispunten voor Mark

- **F4 — /anonymized + /export geven de volledige de-identified tekst aan elke
  key-houder zonder grant · FIXED+verified (2026-08-31).** Mark koos: afschermen
  achter een read-scope. Opt-in corpus-read-scope in de core: beide endpoints
  gegate't door `WORDSWORTH_CORPUS_READ_LABELS` (leeg=uit, non-breaking;
  fail-closed voor None-caller). Pure `authorize_corpus_read()` + guard vóór
  DB-access. Gedeployed `sha-55bd145`, configmap `CORPUS_READ_LABELS=console,cli`.
  Live bewijs: /anonymized console-key 200 / test-key 403; /export cli-key 200 /
  test-key 403; /search+/hybrid test-key 200 (metadata blijft open, alleen
  full-text gescoped). CARDINAL ok. (Was ontwerp-beslispunt.)
- **F2 (latent) — `WORDSWORTH_VC_REQUIRED=true` met een publieke test-issuer** wordt
  teniet gedaan door de ingebedde test-VC. Nu inactief (REQUIRED=false). Guardrail:
  nooit REQUIRED aan met een test/publieke issuer; echte afdwinging = niet-publieke
  issuer + holder-binding (key-binding JWT + audience/nonce).

## Schoon bevonden

- `/documents/{id}/anonymized` (boomhuis-sessie bouwde 't; beide verifieerden):
  zelfde trust-niveau als het al bestaande `/export/anonymized.zip`, niet in
  `EXEMPT_PATHS`, geeft uitsluitend pseudonimizer-output terug (nooit klare PII).
- Deploy dwingt auth af: live-check zonder `X-API-Key` → 401 (alleen `/health` 200).
