# Baton — security-review van de auth-laag (2026-09-12)

Uitgevoerd als lezende werksessie (`!sessie ratatoskr`) op verzoek van
`technical-debt-11-09` §4.1, tegen de code op `main` na de splitsing van
`chat/auth.py`. Geen live aanvallen uitgevoerd; alle bevindingen zijn uit de
code geredeneerd, met een nameet-stap per bevinding.

Kosten: 6m17s, $0.76, 31 beurten.

**Status:** F1 en F2 zijn blokkerend voor het openstellen naar een derde
(`technical-debt-11-09` §5.1). F3 en F4 gaan in dezelfde PR mee.

---

Security-review auth-stack (`technical-debt-11-09` §4.1), gelezen tegen de code op `main`, geen live-aanvallen uitgevoerd. Vier bevindingen met reproduceerbaar pad, plus wat schoon bevonden is en wat ik niet kon nagaan.

## Bevindingen

**F1 — setup-link is niet écht eenmalig: race geeft twee eigenaars · High**
- **Entry:** `POST /api/setup` met een geldige setup-token, tweemaal vrijwel gelijktijdig.
- **Wat een aanvaller stuurt:** twee requests met hetzelfde `token`, verschillende `naam`/`wachtwoord`, binnen het tijdvenster van één scrypt-hash (tientallen ms — ruim genoeg voor twee losse verbindingen).
- **Defect:** `chat/auth_routes.py:125-138`. `setup()` valideert de token (`invite_valid`/`setup_token_valid`), roept dán `_create_account()` (die zelf een scrypt-hash + INSERT doet) aan, en markeert de token pas ná die aanroep als gebruikt (`auth.use_invite(token)` op regel 136). Tussen validatie en markering ligt dus een venster waarin een tweede request dezelfde token óók geldig vindt. De `store.person_count() > 0`-gate aan het begin (regel 127) raced op dezelfde manier. Vergelijk `use_invite()` verderop in hetzelfde bestand (regels 141-148): die markeert wél éérst (`if not auth.use_invite(token): return 403`) en dan pas `_create_account()` — de comment "mark first: single-use, even in a race" laat zien dat dit patroon bekend was, alleen niet toegepast in `setup()`.
- **Wat een aanvaller wint:** een tweede permanente eigenaar-account (`eigenaar=1`) uit één setup-link die bedoeld is voor precies één persoon. Voor een installatie die straks een derde onboardt via deze link is dat een blijvende, niet-triviaal te detecteren backdoor.
- **Kleinste fix:** in `setup()` de volgorde van `use_invite()`/`_create_account()` omdraaien, zoals in `use_invite()` verderop. Sluit de invite-tak. Voor de legacy-tak (`setup_token_valid`, geen invite-rij) is dat niet genoeg — daar helpt een partial unique index (`CREATE UNIQUE INDEX ... ON personen(eigenaar) WHERE eigenaar=1` in `auth_store.py`'s `SCHEMA`) beter: `create_person()` vangt `sqlite3.IntegrityError` al af (regel 91-92) en geeft dan gewoon `None`/409 terug, ongeacht race of pad. Dat dekt beide takken met één regel.
- **Nameten:** twee gelijktijdige `POST /api/setup` met dezelfde token en verschillende namen → precies één 201, de ander 403/409; `SELECT COUNT(*) FROM personen WHERE eigenaar=1` blijft 1.

**F2 — eigen "anti-timing"-code lekt juist een timingverschil · Medium**
- **Entry:** `POST /api/login` met een niet-bestaande naam vs. een bestaande naam + fout wachtwoord.
- **Defect:** `chat/auth_routes.py:72-76`. Voor een bekende gebruiker kost `password_matches()` precies één scrypt-hash. Voor een onbekende naam wordt éérst `auth_factors.hash_password("x", n=2**14)` aangeroepen (nóg een scrypt-hash, met eigen salt) én daarna `password_matches()` — dus twéé scrypt-hashes. De bedoelde gelijkschakeling (comment regel 73-74) doet het tegenovergestelde: onbekende namen worden merkbaar trager dan bekende, in plaats van gelijk.
- **Wat een aanvaller wint:** precies het lek dat de docstring van dit bestand (regel 8-9) zegt te voorkomen — met voldoende samples (herhaalde metingen, N=2^14 scrypt is tientallen ms, dus 2× is ruim boven normale netwerkjitter) is te onderscheiden of een gebruikersnaam bestaat.
- **Kleinste fix:** één vaste dummy-hash bij module-load berekenen (niet per request) en die rechtstreeks aan `password_matches()` geven voor het onbekende-naam-pad, zodat beide paden precies één scrypt-hash kosten.
- **Nameten:** response-tijd `naam=<bestaat-niet>` vs. `naam=<bestaat>,wachtwoord=fout` moet statistisch niet meer te onderscheiden zijn (bv. Mann-Whitney over ≥100 samples elk).

**F3 — X-Forwarded-For blind vertrouwd, verkeerde hop gelezen · Medium**
- **Entry:** elke request naar `/api/login`, `/api/setup`, `/api/uitnodiging/gebruik` met een zelfgekozen `X-Forwarded-For`-header.
- **Defect:** `chat/auth_routes.py:29-33`. `_source()` gebruikt de header onvoorwaardelijk — geen check dat de request van een vertrouwde proxy komt (bv. `h.client_address[0]` op loopback) — én pakt `.split(",")[0]`, het éérste (door de client zelf te zetten) element. Een reverse proxy die standaard `X-Forwarded-For: $proxy_add_x_forwarded_for` doet (nginx-default) ván de client ontvangen waarde vóóraan laat staan en de échte peer-IP er ná plakt; de code leest dus precies het door de aanvaller gekozen deel.
- **Wat een aanvaller wint:** de bron-sleutel (`bron:*`) in de rem (`chat/auth_throttle.py`) telt per verzonnen IP apart — met een andere `X-Forwarded-For`-waarde per poging blijft die teller altijd op 0. De naam-sleutel blijft intact (3 gratis pogingen, dan oplopend), dus geen ongelimiteerde brute-force op één account, maar wél ongehinderd breed proberen over veel namen vanaf één echte bron — exact het scenario dat de rem-comment (`auth_throttle.py:5-7`) zegt te voorkomen.
- **Kleinste fix:** header alleen vertrouwen als `h.client_address[0]` in `("127.0.0.1","::1")` zit (matcht het gedocumenteerde deploy-model: proxy op dezelfde machine, `BIND_ADDR=127.0.0.1`, zie `docs/how-to/installeren.md:70-76`), én dan het láátste element van de lijst nemen (`split(",")[-1]`), niet het eerste.
- **Nameten:** vanaf een niet-loopback peer met verzonnen `X-Forwarded-For` → rem telt op het echte peer-adres; vanaf loopback met proxy-achtige header → rem telt op het laatste (proxy-toegevoegde) adres.

**F4 — geen bovengrens op gelijktijdige scrypt-hashes op open routes · Medium (alleen codepad, niet live getest)**
- **Entry:** `POST /api/login` / `/api/setup` / `/api/uitnodiging/gebruik` — alle drie vóór de sessie-gate (`OPEN` in `chat/auth_routes.py:26`), elk minstens één scrypt-hash (16 MiB, `chat/auth_factors.py:29`) per poging.
- **Defect:** `ThreadingHTTPServer` (`chat/server.py:160`) spawnt onbeperkt een thread per verbinding; geen semafoor of limiet op gelijktijdige hash-operaties in `auth_routes.py`. Elke gelijktijdige poging met een andere naam/bron ontwijkt de rem (des te makkelijker in combinatie met F3), en door F2 kost een onbekende naam zelfs dubbel.
- **Wat een aanvaller wint:** met N gelijktijdige verbindingen ~N×16 MiB geheugendruk plus CPU, op een self-hosted VM met beperkt geheugen een reëel DoS-risico.
- **Kleinste fix:** een bounded semaphore (bv. grootte 4-8) rond de scrypt-aanroepen in `log_in`/`_create_account`, 429 teruggeven bij verzadiging.
- **Niet gedaan:** ik heb dit niet live tegen een draaiende instantie getest — geen destructieve DoS-test uitgevoerd, alleen het codepad nagelopen.

## Schoon bevonden (expliciet tegen de aandachtspunten uit de opdracht)

- **Scrypt-parameters** (`auth_factors.py:29`, N=2^14/r=8/p=1, 16 MiB): dit is OWASP's gedocumenteerde ondergrens voor geheugen-beperkte omgevingen, niet onveilig; de reden (OpenSSL-limiet) staat er goed bij.
- **Sessietoken generatie/vergelijking:** `secrets.token_urlsafe(32)` (256 bit CSPRNG), alleen de sha256-hash in de database (`auth.py:29-32`), lookup via exacte match — geen praktisch uit te voeren timing-aanval op een 256-bit ruimte.
- **CSRF:** serverzijdig aan de sessie gebonden, `hmac.compare_digest` (`auth.py:92-94`), verplicht op elke schrijvende route via `gate(writes=True)`.
- **Cookie vs. database:** cookie draagt uitsluitend de rauwe token; database draagt uitsluitend de hash + metadata — precies het bedoelde model, geen mismatch gevonden.
- **Uitnodigingen (niet-eigenaar-pad):** `use_invite()` in `auth_routes.py` markeert wél vóór het aanmaken van het account; bestaande test (`test_auth_routes.py:128-136`) dekt dit al.

## Kon ik niet nagaan

- Werkelijke timingmeting over het netwerk voor F2 (alleen redenering uit de code: 2× scrypt vs. 1×).
- Of de daadwerkelijke reverse-proxy-config bij Mark (of bij een toekomstige derde) `X-Forwarded-For` overschrijft of aanvult — geen proxy-config in de repo; `docs/how-to/installeren.md` zegt alleen "zorg dat de proxy hem zet", niet hoe.
- Live geheugengedrag onder gelijktijdige requests (F4) — geen DoS-test uitgevoerd.
- SQLite write-serialisatie onder echte gelijktijdige belasting (F1) — geredeneerd vanuit het WAL/locking-model, niet met een live race-test tegen deze `auth_store.py` bevestigd.
- Passkeys/OIDC, genoemd in `auth.py:6-7` als op te richten in change `inloggen-per-persoon` — niet in de gevraagde bestandenlijst, dus niet meegenomen.

Voorstel: F1 en F2 als blokkerend voor 5.1 (poort naar een derde), F3/F4 kunnen mee in dezelfde PR. Verdict past in `handover/` in de vorm van 2026-08-30; dat schrijven is aan de mens/@bouwer die dit oppakt.

— session `ratatoskr` · 6m17s · $0.76 · 31 turns