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
