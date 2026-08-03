# AthleteWeb

Web Experience Layer jest obecnie głównym środowiskiem prototypowania i walidacji UX Athlete Platform. Aplikacja używa Vite, TypeScript, semantycznego HTML i CSS bez frameworka UI.

## Uruchomienie

```bash
cd web/AthleteWeb
npm install
npm run dev
```

Vite domyślnie udostępnia aplikację pod adresem `http://localhost:5173/`.

Walidacja produkcyjna:

```bash
npm run build
npm run test
```

## Architektura

Docelowy przepływ danych:

```text
AthleteDashboard payload v1.0
→ MorningBriefingPresentation
→ UI
```

W bieżącym sprincie UI otrzymuje wyłącznie deterministyczne Preview Data. Mapper payloadu nie jest jeszcze zaimplementowany. `MorningBriefingPresentation` nie zna backendu, domeny ani reguł biznesowych.

Web i zachowany klient SwiftUI mają docelowo konsumować ten sam wersjonowany kontrakt backendowy. Logika domenowa pozostaje wyłącznie w backendzie; klienci odpowiadają za mapowanie prezentacyjne i renderowanie.

## PWA

Manifest i tymczasowa ikona pozwalają uruchamiać prototyp w trybie `standalone`. Service Worker oraz cache offline nie należą do obecnego zakresu.
