---
type: handover-baton
van: security-review-sessie + boomhuis (tweede, onafhankelijke blik)
naar: Mark
status: deels-open
onderwerp: geautoriseerde security-pass wordsworth-PII-pad + boomhuis-comms
datum: 2026-08-30
scope: MWest2020/wordsworth (homelab) + boomhuis chat-backend. Alma (prod) OUT-OF-SCOPE.
autorisatie: Marks eigen infra/repo's; read/gerichte probes, geen DoS/destructief.
artefact_links:
  - wordsworth-console (live): https://mwest2020.github.io/wordsworth-console/  # commit f15571d
  - wordsworth F1/F3-mitigaties: MWest2020/wordsworth (auth per-caller keys + grant-scoping)
next_step: Mark kiest de comms-fix (token / tailscale / beide); dan sluit boomhuis de Medium.
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

### F3 — ongescopete grants reveal op álle docs · Low/Med · FIXED+verified
- **Entry:** `POST /documents/{id}/reveal` met een global grant.
- **Defect:** `grants.py:39` markeert `document_id=None` als "global"; `authorize()`
  (r.67) slaat de doc-check over als `document_id is None` ⇒ één grant reveal-t op
  elk document. Live-repro: één `[PERSON]`-grant → 200 op twee doc-id's.
- **Fix (peer):** Console geeft nu optioneel `document_id` mee (scoping).
- **Bewijs:** gescopete grant → reveal op eigen doc 200, op ander doc 403.

### Comms — chat-backend bindt 0.0.0.0, geen auth, tekent als mark · Medium · OPEN
- **Entry:** `POST http://192.168.178.60:8090/api/send` (ook `/api/channels/create|delete`).
- **Defect:** `chat/server.py` bindt op `("0.0.0.0", 8090)` zonder auth en tekent
  elk bericht als `mark`. Bereikt vanaf een andere host over de LAN. Elke node op
  het homelab-net (incl. andere agents) kan als mark posten / kanalen CRUD-en.
- **Belangrijke correctie op de eerste fix-formulering:** tailscale draait NIET op
  de VM (enige interface eth0 192.168.178.60; geen 100.x). "Tailnet-only" komt van
  een subnet-router elders. Binden op een 100.x kan dus niet (bind faalt → chat
  plat); binden op 192.168.178.60 sluit de LAN-exposure niet.
- **Echte opties (Marks keuze):** (1) app-token op de write-endpoints —
  topologie-onafhankelijk, geen nieuwe infra; (2) tailscale op de VM + bind op de
  dan-echte 100.x — socket-niveau tailnet-only, vergt een auth-key. Sterkste = beide.
- **Re-test na fix:** vanaf niet-tailnet host naar VM-LAN-IP:8090 → connection
  refused (was 200); geldig kanaal alleen met token/over-tailnet.

## Beslispunten voor Mark (geen bug)

- **F4 — /anonymized + /export geven de volledige de-identified tekst aan elke
  key-houder zonder grant.** CARDINAL ok (nooit klare PII), maar breder dan
  snippets. Wel of niet toestaan = ontwerpkeuze.
- **F2 (latent) — `WORDSWORTH_VC_REQUIRED=true` met een publieke test-issuer** wordt
  teniet gedaan door de ingebedde test-VC. Nu inactief (REQUIRED=false). Guardrail:
  nooit REQUIRED aan met een test/publieke issuer; echte afdwinging = niet-publieke
  issuer + holder-binding (key-binding JWT + audience/nonce).

## Schoon bevonden

- `/documents/{id}/anonymized` (boomhuis-sessie bouwde 't; beide verifieerden):
  zelfde trust-niveau als het al bestaande `/export/anonymized.zip`, niet in
  `EXEMPT_PATHS`, geeft uitsluitend pseudonimizer-output terug (nooit klare PII).
- Deploy dwingt auth af: live-check zonder `X-API-Key` → 401 (alleen `/health` 200).
