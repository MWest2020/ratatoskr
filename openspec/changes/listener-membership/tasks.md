# Tasks: listener-membership

- [x] 1.1 `agents/topology.py`: `poll_channels(run, fallback)` (relay-lijst ∪
      channels.yml, ~60s cache, vangnet bij fout) + `members(run, cid)` (member-
      pubkeys, ~60s cache, lege fetch overschrijft geen goede cache).
- [x] 1.2 `agents/prompts.py`: context/prompt-bouwers (`channel_knowledge`,
      `live_text`, `roster_text`, `build_prompt`) uit listener.py gelicht zodat
      listener.py ≤200 regels blijft.
- [x] 1.3 `agents/listener.py`: target-regel = handbook-scope OF relay-lid
      (`members`); poll-set via `topology.poll_channels`; thread-vervolg
      ongewijzigd.
- [x] 1.4 Live smoke: @coordinator in #red-team → antwoord; @<agent> in een via de
      app aangemaakt kanaal → antwoord; def-kanaal (bv. @architect in
      #architectuur) blijft werken; geen dubbel-antwoord.
      Bewijs (listener-log): de live smoke dekt het ROUTING-happy-path — `mention
      @coordinator in #red-team` → `coordinator antwoordde in #red-team (mention)`.
      #red-team staat niet in coordinators handbook-`chat.channels: [general]`, dus
      dit kán alleen via de relay-lidmaatschap-tak; def-kanaal (@architect/
      #architectuur) en de #general-vervolg-tak bleven werken, geen dubbel-antwoord.
      Deze smoke is ná ELKE fix-ronde opnieuw gedraaid en bleef groen (t/m r7). De
      EDGE-cases die r6/r7 raakten (lege/onparsebare relay-lijst, cid-dedup, luie
      members) zitten niet in dit happy-path maar zijn gedekt door de 12 unittests in
      `agents/test_topology.py` — die vormen samen het regressiebewijs.
- [x] 1.5 r1-fixes: `poll_channels` filtert relay-junk (`_HIDE`) en laat de
      channels.yml-cid winnen bij naam-botsing (relay overschrijft niet meer); een
      mislukte/lege fetch behoudt de goede cache i.p.v. terug te vallen op de kale
      fallback; `seen` wordt per NIEUW kanaal geprimed (`seeded`) zodat de listener
      niet op de historie van een later-verschenen kanaal reageert. Offline getest.
- [x] 1.6 r2-fixes: reader = coordinator-sleutel (lid overal → ziet alle kanalen);
      `get_messages` geeft None bij mislukte read (≠ leeg) zodat de seed niet te
      omzeilen is; `send` checkt rc en logt eerlijk (geen valse 'antwoordde');
      `members` cachet een echt-leeg kanaal maar behoudt de cache bij een fout;
      `mentioned` = woordgrens-match (`@architect` ≠ `@architectuur`); `_HIDE`-comment
      legt uit waarom PREFER niet nodig is. Tests in agents/test_topology.py (6, groen).
- [x] 1.7 r3-fixes: thread-vervolg terug naar def-kanaal-only (membership verbreedt
      alléén de mention-tak, conform spec); `_rows` geeft None bij non-dict JSON
      (geen AttributeError-crash); `members` cachet geen negatieve lege entry bij een
      eerste mislukte fetch; `mentioned` heeft nu óók een linker-woordgrens
      (`deploy@bouwer` matcht niet); pure `topology.is_scoped` (getest); provider-naad
      naar `providers.py` (listener 189 regels); README + design-kostennoot bijgewerkt;
      test-commando in de docstring rechtgezet. Tests: 9, groen.
- [x] 1.8 r4-fixes: `buzz_run` vangt subprocess-excepties (timeout/OSError) → lege
      string, zodat de belofte 'faalt → val terug' óók bij een timeout houdt en de
      poll-lus niet crasht; `_rows` geeft None voor een dict zonder de sleutel
      (bv. `{"error":..}`, geen valse lege-lijst-cache); reader-fallback logt een
      waarschuwing als coordinator ontbreekt; smoke-bewijs vastgelegd in 1.4. Tests: 9.
- [x] 1.9 r5-fixes: óók `get_messages`/`send` vangen subprocess-excepties (timeout/
      OSError) → None/False, zodat één timeout de daemon niet doodt (de `while True`
      is ongeguard); design eerlijk over de verruimde `get_messages`-kostenpost
      (poll-set = channels.yml ∪ alle open relay-kanalen, niet meer de curatie) +
      de bewuste vervolg-tak-tradeoff. Tests: 9, groen.
- [x] 1.10 r6-fixes: `poll_channels` behandelt een geslaagd-maar-lege KANAALlijst als
      mislukt (`if not rows`) → verliest geen ontdekte kanalen; spec/design zetten het
      onderscheid recht (mislukt vs geslaagd-leeg: kanaallijst nooit legitiem leeg,
      ledenlijst wél); `is_scoped` neemt de leden LUI (0-arg callable) → geen members-
      fetch voor een def-gescopt kanaal. Tests: 11 (incl. lege-lijst + laziness), groen.
- [x] 1.11 r7-fixes: poll_channels dedupt nu op NAAM én CID (channels.yml canoniek
      eerst) → een kanaal onder twee namen met dezelfde cid staat maar één keer in de
      poll-set (geen dubbele poll); `_rows` valideert dat de sleutelwaarde een lijst
      is (`{"channels":{...}}`/`"x"` → None, geen crash op `.get`). Tests: 12, groen.
- [x] 1.12 r8-fixes: `poll_channels` cachet niet meer bij een EERSTE mislukking
      (consistent met `members`: volgende tick probeert opnieuw); vervolg-tak-def-only
      staat nu ook in de spec-delta; cid-dedup-keuze (channels.yml canoniek bij
      relay-hernoeming) + `seen`-groei als follow-up in design vastgelegd; smoke-bewijs
      eerlijk herkaderd (happy-path live, edges via de 12 unittests).
