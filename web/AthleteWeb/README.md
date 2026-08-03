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

Sprint 2 dopracowuje wyłącznie jakość tego samego ekranu: lżejszy briefing, większą typografię i whitespace, uproszczoną decyzję, czytelniejszy postęp celu oraz skróty w formie spokojnej listy ustawień. Zakres funkcjonalny pozostaje bez zmian.

## Stany prezentacyjne

`MorningBriefingPresentationState` jest discriminated union rozróżnianym przez pole `kind`. Nie używa niezależnych flag, dlatego nie może reprezentować sprzecznych kombinacji, takich jak jednoczesne `loading` i `failure`.

| Stan | Znaczenie | Preview |
|---|---|---|
| `ready` | kompletny i aktualny briefing | `?state=ready` |
| `partial` | decyzja jest dostępna, ale jawnie brakuje części źródeł | `?state=partial` |
| `unavailable` | danych jest za mało, aby przedstawić wiarygodną decyzję | `?state=unavailable` |
| `stale` | briefing pozostaje dostępny, ale pochodzi ze starszych danych | `?state=stale` |
| `loading` | krótki, spokojny stan oczekiwania | `?state=loading` |
| `failure` | pobranie lub przetworzenie danych zakończyło się błędem | `?state=failure` |

`partial` opisuje kompletność danych użytych przez nadal dostępny briefing. `stale` opisuje ich aktualność. `unavailable` jest oczekiwanym stanem produktu wynikającym z niewystarczających danych, natomiast `failure` oznacza błąd operacji i jako jedyny udostępnia akcję ponowienia.

Nieznana lub pominięta wartość `state` bezpiecznie wybiera `ready`. Query string jest wyłącznie mechanizmem Preview i nie pojawia się w interfejsie użytkownika.

Web i zachowany klient SwiftUI mają docelowo konsumować ten sam wersjonowany kontrakt backendowy. Logika domenowa pozostaje wyłącznie w backendzie; klienci odpowiadają za mapowanie prezentacyjne i renderowanie.

## PWA

Manifest i tymczasowa ikona pozwalają uruchamiać prototyp w trybie `standalone`. Service Worker oraz cache offline nie należą do obecnego zakresu.
