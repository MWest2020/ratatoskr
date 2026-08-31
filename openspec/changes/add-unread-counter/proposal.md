## Why

De kanaallijst toont niet welke kanalen nieuwe berichten hebben. Je moet elk
kanaal openen om te zien of er iets is — dat schaalt slecht nu er meer
projectkanalen bijkomen (#wordsworth, #netnl, #netnl-api).

## What Changes

- **`/api/overview`**: één endpoint dat per kanaal het aantal berichten
  teruggeeft (backend fan-out naar buzz, kort server-side gecachet met een
  single-flight-lock zodat de poll de relay niet hamert; een mislukte fan-out
  geeft 502, geen stille lege lijst).
- **PWA-kanaallijst**: een ongelezen-badge per kanaal, berekend uit het verschil
  tussen het huidige aantal en wat je op dít apparaat het laatst zag
  (localStorage, per device). Openen van een kanaal markeert het als gelezen.
