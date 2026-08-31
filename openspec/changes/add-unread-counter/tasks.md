# Tasks: add-unread-counter

- [ ] 1.1 Backend `/api/overview` — per kanaal `{name, id, count, latest}` via
      buzz-fan-out, met een korte server-side cache (enkele seconden).
- [ ] 1.2 PWA — ongelezen-badge per kanaal in de kanaallijst; "gezien" per device
      in localStorage; openen van een kanaal markeert het als gelezen; periodieke
      overview-poll die de badges bijwerkt.
