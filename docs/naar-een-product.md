---
status: draft
last_reviewed: 2026-09-09
---

# Van PoC naar product — wat er dan breekt

*Ontwerpstuk, geen change. Er staan drie beslissingen open die alleen Mark kan
nemen; die staan onderaan. Zodra die genomen zijn valt dit uiteen in vijf
OpenSpec-changes, en dán pas is er iets te bouwen. Bewust nog geen change:
zonder die drie antwoorden zijn er ook geen spec-deltas te schrijven.*

## Waarom dit stuk bestaat

Boomhuis is gebouwd als coördinatielaag voor één mens en zijn agents. De
richting is nu een **installeerbare app voor derden**: installeren, aangeven
welke kant je op werkt (dev, project lead, cybersecurity), en een paar
voorgeconfigureerde agents krijgen. Zettelkast blijft de plek waar de mens
snel aangeeft wat interessant is; de agents leiden daaruit af wat opgepakt
moet worden of assisteren sneller bij een vraag.

Dat is geen uitbreiding van het huidige ontwerp — het breekt er vier
invarianten van. Beter nu benoemd dan tijdens de bouw ontdekt.

## Wat er breekt aan het huidige ontwerp

**1. Er is geen authenticatie.** Lezen in de comms-API is volledig open;
`auth.py` bewaakt alleen schrijven, en de docstring zegt zelf dat het tailnet
"de primaire control" is. Het tailnet is niet een extra slot bovenop een deur,
het ís de deur. Bij een derde partij bestaat dat tailnet niet, en zijn er
bovendien meerdere mensen. Authenticatie is dus geen randvoorwaarde maar het
eerste bouwwerk.

**2. "Uitsluitend via het tailnet" is normatief** (`relay-deployment/spec.md`)
en kan niet blijven staan. Wat ervoor in de plaats komt is een keuze, niet een
detail — zie *Open beslissing A*.

**3. Identiteiten en sleutels leven in Marks git.** `identities.yml` staat in
deze repo, privésleutels via SOPS+age met Marks sleutel. Een installatie bij
een ander moet zijn eigen sleutelpaar per identiteit genereren, bij
installatie, in een sleutelopslag op die installatie — niet in een repo.

**4. Agents draaien op Marks infrastructuur.** De chat-native agents draaien
als `claude -p` op de relay-host, op Marks abonnement; de gekooide agents zijn
habitat-Jobs op Marks cluster. Geen van beide kun je aannemen bij een klant.
Wie betaalt en draait het model, is de vraag die de hele agent-laag bepaalt —
zie *Open beslissing B*.

## Wat een MVP wél zou zijn

Klein gehouden, want "in weken":

- **Eén installatie = één team.** Iedereen in de installatie ziet alles.
  Per-gebruiker-rechten zijn een latere change; ze verdubbelen het ontwerp en
  zijn niet nodig om te bewijzen dat het werkt.
- **Inloggen met iets dat bij een persoon hoort** — passkeys of OIDC tegen de
  identiteitsvoorziening die de klant al heeft. Geen gedeeld token: dat is wat
  we nu hebben en het schaalt niet naar meerdere mensen.
- **Onboarding in drie schermen**: installatie benoemen, richting kiezen
  (dev / project lead / cybersecurity), model-toegang koppelen. Daarna staan
  er drie tot vijf agents klaar met kanalen en mandaten die bij die richting
  horen.
- **Agentdefinities gaan mee met de app**, niet met Marks handbook-repo. De
  handbook-koppeling blijft bestaan voor wie er een heeft.
- **Zettelkast als notitieruimte per installatie**: de mens markeert wat
  interessant is, agents lezen dat en stellen voor wat opgepakt wordt. Dat is
  een echte integratie, geen doorverwijzing.

## Open beslissingen

**A. Self-hosted of gehost?** Aanbeveling: **self-hosted** voor de MVP — een
compose-stack of ExApp die de klant zelf draait. Dan blijft "geen publieke
voordeur" hun keuze in plaats van onze belofte, en het past bij hoe de rest
van het portfolio geleverd wordt (Wanderer-ExApp, habitat). Gehost betekent
een dienst met accounts, betalingen, verwerkersafspraken en 24/7 — dat is een
bedrijf, geen MVP.

**B. Wie levert de modeltoegang?** Aanbeveling: **de klant brengt zijn eigen**
— een Claude-abonnement per gebruiker (de `claude -p`-weg die hier al draait)
of een API-sleutel van de klant. Zelf modelkosten dragen maakt elke gratis
proefinstallatie een rekening.

**C. Eén team per installatie, of meteen rechten?** Aanbeveling: **één team**.
De grens is dan de installatie, en dat is uitlegbaar.

## Impact

- Nieuwe capability `auth` (inloggen, sessies, per-installatie sleutelopslag).
- `relay-deployment`: de tailnet-eis wordt een deployment-optie in plaats van
  een invariant.
- `identity-registry`: sleutels bij installatie genereren, niet uit git.
- `chat-native-agents`: definities per richting mee in de app; runtime achter
  een seam zodat "wie draait het model" een instelling is.
- Nieuwe capability voor onboarding.

Elk van die vijf is een eigen change, in die volgorde — zonder
authenticatie heeft de rest geen fundament. Dit stuk is de kaart, niet
de rit.
