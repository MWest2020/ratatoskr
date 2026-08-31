# 📌 wordsworth — actuele context

> Dit is de "pinned" context van #wordsworth: het wordt als kennis aan elke agent
> in dit kanaal meegegeven én (straks) bovenaan het kanaal getoond in de app.
> Houd 'm kort en actueel — de meest relevante status/overdracht.

**Wat:** soevereine pipeline die (Nederlandse) overheidsdocumenten omzet naar een
doorzoekbaar, privacy-veilig corpus. `ingest → extractie → anonimiseer/pseudonimiseer
→ store → index → hybride search → rank`. Publiek: `MWest2020/wordsworth`.

**Cardinale invariant:** nooit klare PII richting de index; pseudonimisatie is
omkeerbaar+gecontroleerd en zit vóór indexeren. Audit is append-only + hash-chained.

**Laatste (2026-08-30):** geautoriseerde security-review afgerond. Endpoints
`GET /documents/{id}/anonymized` (schoon) + reveal (grant-gated). F1 (per-caller
keys) + F3 (grant-scoping) FIXED+verified. Deploy dwingt api-key-auth af.
Beslispunten open: F4 (/anonymized geeft volledige de-identified tekst aan elke
key-houder, geen klare PII) + F2 (VC-REQUIRED nooit met publieke test-issuer).
