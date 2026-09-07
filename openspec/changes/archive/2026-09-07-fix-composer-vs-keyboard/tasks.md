# Tasks: fix-composer-vs-keyboard

- [x] 1.1 `--app-h` uit `visualViewport.height` (inline in de shell), body volgt
      met `height:100dvh; height:var(--app-h, 100dvh)`.
- [x] 1.2 `interactive-widget=resizes-content` in de viewport-meta.
- [x] 1.3 Service-worker-cache naar `v6`.
- [x] 1.4 Gemeten op een iPhone-13-viewport: bij een visuele viewport van 330px
      krimpt de shell mee (`--app-h: 330px`) en blijft de composer zichtbaar
      (bottom 330 ≤ 330); normaal 664/664.
- [x] 1.5 `openspec validate --strict` groen.
