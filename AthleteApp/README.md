# AthleteApp

Natywny klient iOS Athlete Platform. Pierwsze dwa sprinty udostępniają dopracowany, statyczny ekran Morning Briefing zbudowany w SwiftUI dla iOS 18+.

## Granice Sprintu 1

- dane pochodzą wyłącznie z `MorningBriefingPreviewData`;
- `MorningBriefingPresentation` jest modelem prezentacyjnym, a nie domenowym ani transportowym;
- `MorningBriefingViewModel` stanowi przyszły cel mapowania z `AthleteDashboard`;
- aplikacja nie łączy się z backendem, API ani Apple Health;
- dolna nawigacja komunikuje przyszłą strukturę, ale tylko karta „Dzisiaj” jest aktywna.

## Jakość interfejsu

- semantyczne kolory systemowe i adaptacyjne tokeny akcentu obsługują Light oraz Dark Mode;
- układ reaguje na Dynamic Type, w tym rozmiary accessibility;
- elementy nawigacji zachowują minimalny 44-punktowy obszar dotyku i jawne opisy VoiceOver;
- krótka animacja wejścia oraz postępu respektuje ustawienie Reduce Motion;
- trzy samowystarczalne Preview pokrywają wygląd domyślny, Dark Mode i powiększony tekst.

## Struktura

- `App/` — composition root aplikacji;
- `Features/MorningBriefing/` — widok i view model funkcji;
- `Components/` — współdzielone, bezstanowe komponenty UI;
- `Theme/` — tokeny wizualne;
- `Models/` — modele prezentacyjne niezależne od backendu;
- `PreviewData/` — deterministyczne dane demonstracyjne;
- `Resources/` — katalog zasobów aplikacji.

## Walidacja

Otwórz `AthleteApp.xcodeproj` w Xcode 17 lub nowszym, wybierz symulator iOS 18 i uruchom schemat `AthleteApp`. Preview znajduje się w `MorningBriefingView.swift` i nie wymaga zewnętrznych zależności.
