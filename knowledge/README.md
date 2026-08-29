# knowledge — per-kanaal kennis

Conventie: `knowledge/<kanaalnaam>.md` wordt door de listener als vaste context
meegegeven aan élke agent-beurt in dat kanaal (idee geleend van Switch:
"attached knowledge per room"). Zo is een agent beter geaard zonder dat je het
in elke prompt herhaalt.

- Bestaat het bestand niet → geen extra context (geen fout).
- Max ~4000 tekens per kanaal (afgekapt).
- Voorbeeld: `architectuur.md` geeft @architect de ecosysteem-principes.

Nieuw kennisbestand = gewoon `knowledge/<kanaal>.md` aanmaken; de listener pakt
het op bij de volgende beurt (geen herstart nodig voor de inhoud).
