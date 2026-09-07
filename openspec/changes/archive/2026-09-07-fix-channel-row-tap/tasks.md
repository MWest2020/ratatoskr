# Tasks: fix-channel-row-tap

- [x] 1.1 `chat/app.js`: `row.onclick` in plaats van handlers op `.cmeta`,
      `.hash` en `.unread`; verwijderknop houdt `stopPropagation`.
- [x] 1.2 Live nagemeten op de draaiende VM (iPhone-viewport): tik naast de naam
      wisselt van kanaal én sluit de lade; verwijderknop opent nog steeds de
      bevestiging en wisselt niet van kanaal.
- [x] 1.3 `openspec validate --strict` groen.
