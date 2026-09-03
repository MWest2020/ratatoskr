# Tasks: add-mention-add-agent-ux

- [x] 1.1 `/api/send`: geen geforceerde `--mention`; niet-lid-mention → `409
      {missing_agent, known, channel}`.
- [x] 1.2 `/api/channel/add-member` + `roster.agent_pubkey`.
- [x] 1.3 Frontend: pop-up "toevoegen?" + auto-retry na toevoegen; onbekende naam → melding.
- [x] 1.4 MENTION_PUBKEY-workaround verwijderd.
- [x] 1.5 `/api/channels/create` voegt coordinator standaard toe (best-effort; rc
      gecheckt, `channel_id`|`id`); channel-topology spec-delta voor het beleid.
- [x] 1.6 Split naar `chat/actions.py` (server <200); `roster.agent_pubkey`
      (agents-only, case-insensitive); mark/sessies niet toevoegbaar; retry-guard;
      "toch versturen"-escape (force → lid-mention presentation-only).
- [x] 1.7 Live gesmoked: @lid → ok, @niet-lid-agent → 409+toevoegen, @niet-agent →
      409+toch-versturen, add-member → ok, retry → ok, create → coordinator erbij.
- [x] 1.8 r4-fixes: force-retry prompt niet opnieuw (geen loop) + force-versturen na
      add; `create` best-effort losgetrokken (`_add_coordinator`, brede guard + stderr-log,
      `channel_id|id`); `_a_member_of` deterministisch (sorted); topology-spec herschreven
      naar "nieuw kanaal + operator-backfill" (geen valse "elk kanaal"-claim); docstring +
      proposal-payload (`can_force`) rechtgezet.
- [x] 1.9 r5-fixes: `_add_coordinator` geeft altijd bool (False i.p.v. None op
      faalpaden) zodat een mislukte add zichtbaar is; topology-spec noemt geen
      niet-bestaand script meer (operator-backfill generiek); app.js `_postSend`
      zonder dode `tried`-set, gebruikt `j.channel` uit de 409, onder 200 regels;
      `_a_member_of` kiest bij voorkeur een niet-agent-lid als force-anker;
      multi-mention-gedrag in design vastgelegd.
