# Tasks: listener-membership

- [ ] 1.1 `agents/topology.py`: `poll_channels(run, fallback)` (relay-lijst ∪
      channels.yml, ~60s cache, vangnet bij fout) + `members(run, cid)` (member-
      pubkeys, ~60s cache, lege fetch overschrijft geen goede cache).
- [ ] 1.2 `agents/prompts.py`: context/prompt-bouwers (`channel_knowledge`,
      `live_text`, `roster_text`, `build_prompt`) uit listener.py gelicht zodat
      listener.py ≤200 regels blijft.
- [ ] 1.3 `agents/listener.py`: target-regel = handbook-scope OF relay-lid
      (`members`); poll-set via `topology.poll_channels`; thread-vervolg
      ongewijzigd.
- [ ] 1.4 Live smoke: @coordinator in #red-team → antwoord; @<agent> in een via de
      app aangemaakt kanaal → antwoord; def-kanaal (bv. @architect in
      #architectuur) blijft werken; geen dubbel-antwoord.
