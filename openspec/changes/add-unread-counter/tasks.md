# Tasks: add-unread-counter

- [x] 1.1 Backend `/api/overview` — per kanaal `{name, id, count}` via
      buzz-fan-out, met een korte server-side cache (TTL >= poll-interval) plus
      een single-flight-lock tegen thundering herd.
- [x] 1.2 PWA — ongelezen-badge per kanaal in de kanaallijst; "gezien" per device
      in localStorage; openen van een kanaal markeert het als gelezen; periodieke
      overview-poll die de badges bijwerkt; prune van keys voor verwijderde kanalen.
