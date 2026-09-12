# Change: werksessies die ook schrijven

## Why

Mark heeft dit vier keer gevraagd. De eerste keer (2026-09-09) werd het een
LEZENDE werksessie, met een goede reden: geen tweede, ongepoorte weg naar een
commit naast de habitat-kooi. Die reden is nog steeds goed voor *mergen*, maar
hij is te ruim uitgelegd — hij verbiedt nu ook het enige wat Mark elke dag
feitelijk doet.

Want dit is wat er vandaag gebeurt: Mark vraagt iets, ik start een tmux-sessie in
een worktree, die sessie bouwt en opent een PR, en ik blijf ondertussen
aanspreekbaar. Dat werkt. Het is alleen niet beschikbaar in Ratatoskr zelf, en
daarmee is de app een leesvenster op werk dat elders gebeurt.

Mark, 2026-09-12: *"liefst werk ik zo: ik vraag jou wat, jij spawnt tmux sessies
of subagents voor het werk en je bent direct beschikbaar. zo wil ik uiteindelijk
via ratatoskr werken."*

## What Changes

- Een sessietype mag `writes: true` dragen. Zo'n sessie krijgt **een eigen
  git-worktree op een eigen branch**, mag daarbinnen schrijven en `git` en tests
  draaien, en eindigt met een **pull request** — nooit met een merge.
- **Een pre-push hook in die worktree weigert elke push behalve naar de eigen
  branch.** Niet als belofte in een prompt maar als hek: een prompt is te sturen,
  een hook niet.
- De worktree staat **buiten elke draaiende checkout**, dus een sessie kan de
  listener of de live chat niet onder handen nemen.
- De sessie post bij afloop de PR-link in het kanaal waar hij gestart is.
- Lezende sessies veranderen niet. De poortwachter van `habitat-bridge` verandert
  niet: mergen blijft mensenwerk, en de kooi blijft de weg voor gekooide runs.

## Impact

- Nieuw: `agents/work_tree.py`, een type `build` in `agents/sessies.yml`.
- Gewijzigd: `agents/sessies.py` (worktree + ruimere tools als `writes`),
  `agents/session_gate.py` (niet elk type mag schrijven), `docs/how-to/werksessies.md`.
- Spec: `werksessies` krijgt requirements over schrijven, de branch en de hook.
