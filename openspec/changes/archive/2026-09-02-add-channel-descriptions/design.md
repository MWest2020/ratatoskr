# Design: add-channel-descriptions

## 1. Native relay-beschrijving i.p.v. channels.yml naar de app halen

**Keuze:** de beschrijving leeft op het kanaal (relay); `channels list` geeft 'm
mee, de app leest 'm daar.

**Verworpen:** `channels.yml`'s `doel` uit de repo halen (zoals de pinned-context).
De beschrijving hoort bij het kanaal zelf; native houdt de app onafhankelijk van
een repo-fetch en werkt ook voor kanalen die buiten channels.yml om ontstaan.
`channels.yml` blijft de bron waaruit we de beschrijving één keer zetten.

## 2. Subtitel in de lade i.p.v. alleen in de header

**Keuze:** de beschrijving staat als ingekorte subtitel onder elke kanaalnaam in
de lade.

**Verworpen:** alleen tonen bij het geopende kanaal (header). Mark wil per kanaal
zien waar het voor is én of het hoort te werken — dat vraagt een overzicht van
alle kanalen tegelijk, niet één per keer.
