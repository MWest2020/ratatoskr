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
- [ ] 1.4 Live smoke: @coordinator in #red-team → antwoord; @<agent> in een via de
      app aangemaakt kanaal → antwoord; def-kanaal (bv. @architect in
      #architectuur) blijft werken; geen dubbel-antwoord.
- [x] 1.5 r1-fixes: `poll_channels` filtert relay-junk (`_HIDE`) en laat de
      channels.yml-cid winnen bij naam-botsing (relay overschrijft niet meer); een
      mislukte/lege fetch behoudt de goede cache i.p.v. terug te vallen op de kale
      fallback; `seen` wordt per NIEUW kanaal geprimed (`seeded`) zodat de listener
      niet op de historie van een later-verschenen kanaal reageert. Offline getest.
