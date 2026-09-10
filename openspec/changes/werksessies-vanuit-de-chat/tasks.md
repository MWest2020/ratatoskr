# Taken

## 1. Fundament
- [x] 1.1 `agents/relay.py`: buzz-I/O (`buzz_env`, `get_messages`, `send`,
      `buzz_run`) uit `listener.py` lichten; listener blijft ≤200 regels
- [x] 1.2 `agents/sessies.yml`: schema + het type `zettelkast`
- [x] 1.3 `agents/sessies.py`: marker lezen/knippen, machtiging, starten
      (losgekoppeld, gestripte env, pad-begrensde tools), oogsten per tick,
      budget-kill

## 2. Aansluiten
- [x] 2.1 `listener.py`: marker uit een agent-antwoord én uit een mensbericht;
      voortgang en resultaat posten onder de type-identiteit
- [x] 2.2 Weigeringen (onbekend type, niet-gemachtigd, al bezig, vol) melden

## 3. Bewijs
- [x] 3.1 `agents/test_sessies.py`: marker-parsing, knippen, machtiging,
      gelijktijdigheid, budget — offline
- [x] 3.2 Volledige unittests groen (`agents`)
- [x] 3.3 Live: `!sessie zettelkast …` in #general → voortgang + resultaat,
      met de echte vault als werkmap
- [x] 3.4 Meten dat een gewone mention in een ander kanaal doorloopt terwijl
      de sessie draait

## 4. Vastleggen
- [x] 4.1 `agents/README.md` + `docs/how-to/werksessies.md`
- [ ] 4.2 Change archiveren
