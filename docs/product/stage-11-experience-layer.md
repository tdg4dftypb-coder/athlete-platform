# Stage 11 — Experience Layer

## Status klientów

`web/AthleteWeb` jest obecnie głównym środowiskiem fizycznego rozwoju Experience Layer: prototypowania UX, projektowania komponentów i walidacji responsywności. Jest to klient prezentacyjny, nie nowa warstwa logiki produktu.

Projekt `AthleteApp` pozostaje zachowany jako docelowy klient natywny SwiftUI. Jego rozwój zostanie wznowiony po zapewnieniu środowiska pozwalającego wykonywać pełny build i walidować Preview.

## Wspólna granica

Oba klienty mają docelowo konsumować ten sam ścisły kontrakt `AthleteDashboard payload v1.0`. Każdy klient mapuje payload do własnego modelu prezentacyjnego, przygotowanego pod potrzeby danego interfejsu:

```text
AthleteDashboard payload v1.0
→ client presentation model
→ UI
```

Modele prezentacyjne nie są modelami domenowymi. Nie podejmują decyzji, nie interpretują evidence i nie uzupełniają brakujących danych. Cała logika domenowa, decyzje treningowe i rekomendacje pozostają w backendzie.

## Web Morning Briefing

Pierwszy prototyp webowy realizuje zasadę Decision First. Najpierw przedstawia dzisiejszą decyzję i jej narracyjne uzasadnienie, a dopiero dalej zmianę względem wczoraj, plan dnia, cel i skróty. Dane są statyczne i deterministyczne; integracja payloadu pozostaje poza zakresem.

Interfejs jest mobile first, zachowuje ograniczoną szerokość na desktopie i obsługuje Dark Mode, powiększony tekst, widoczny focus oraz `prefers-reduced-motion`.
