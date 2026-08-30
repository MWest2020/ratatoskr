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
next_step: comms-Medium FIXED (tailscale-bind). Rest = ontwerp-beslissingen voor Mark (F4-exposure, optionele app-token) + de baton-conventie zelf.
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
