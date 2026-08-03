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

## Morning Briefing Presentation States

Experience Layer używa jawnego `MorningBriefingPresentationState` jako discriminated union: `ready`, `partial`, `unavailable`, `stale`, `loading` albo `failure`. Każdy wariant zawiera wyłącznie wymagane dla niego dane i nie dopuszcza sprzecznych kombinacji luźnych flag.

- `ready` transportuje kompletny, aktualny briefing;
- `partial` transportuje briefing oraz jawną listę brakujących źródeł; jego Preview Data nie formułują wniosków na podstawie tych braków;
- `unavailable` nie transportuje decyzji, ponieważ danych jest zbyt mało do wiarygodnego wyniku;
- `stale` zachowuje dostęp do briefingu, ale przed treścią pokazuje czas ostatniej aktualizacji;
- `loading` nie posiada danych briefingu i udostępnia stabilny przestrzennie skeleton;
- `failure` opisuje błąd operacyjny oraz jedną akcję ponowienia.

`partial` dotyczy kompletności, a `stale` aktualności danych. `unavailable` jest poprawnym wynikiem braku wystarczających faktów, natomiast `failure` oznacza, że oczekiwana operacja nie mogła się zakończyć.

Query string `?state=<kind>` służy wyłącznie do deterministycznego Preview wszystkich wariantów. Nie jest częścią interfejsu ani przyszłego kontraktu backendowego.

## Web Visual System

Light Mode jest głównym kierunkiem wizualnym Athlete Platform. Jasne neutralne powierzchnie, delikatny cień i pastelowy gradient hero budują spokojny charakter porannej odprawy. Dark Mode jest wariantem systemowym opartym na ciemnych neutralnych powierzchniach bez czystej czerni i zachowuje tę samą semantykę.

Kolory mają stałe znaczenie: zieleń opisuje regenerację, HRV i cele; błękit trening; fiolet sen, refleksję i briefing; pomarańcz odżywianie, obciążenie i uwagę; chłodne szaroniebieskie odcienie informacje neutralne. Kolor wspiera istniejący tekst i znaczniki, ale nigdy samodzielnie nie komunikuje stanu.

Stany prezentacyjne korzystają z tokenów operacyjnych bez zmiany swojej semantyki: `partial` używa spokojnego `info`, `unavailable` wariantu neutralnego, `stale` tokenu `warning`, a `failure` stonowanego `error`. `ready` korzysta z pełnej palety obszarów, natomiast `loading` używa powierzchni neutralnych i łagodnego skeletonu respektującego `prefers-reduced-motion`.

Źródłem kolorów jest jeden katalog Theme w `src/theme/tokens.css`. Katalog obejmuje powierzchnie, trzy poziomy tekstu, akcenty produktowe, statusy operacyjne, focus, postęp, cień oraz trzy punkty gradientu hero. Komponenty nie przechowują własnych wartości kolorów.

## AthleteDashboard mapping boundary

Sprint 5 dodaje ścisłą granicę `unknown → parser → AthleteDashboardPayloadV1 → mapper → MorningBriefingPresentationState`. Kontrakt frontendowy pozostaje oddzielony od modeli prezentacyjnych i nie importuje modeli domenowych. Validation failure prowadzi do `failure`, natomiast poprawny kontrakt bez wystarczającej decyzji prowadzi do `unavailable`. `loading` należy do przyszłej warstwy transportowej i nie jest wynikiem mappera.

Szczegółowy kontrakt, reguły świeżości, ograniczenia payloadu i fixtures opisuje [AthleteDashboard — frontend contract boundary](athlete-dashboard-frontend-contract.md).
