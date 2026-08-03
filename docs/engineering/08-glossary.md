# 08. Glosariusz

> Jednoznaczne definicje pojęć domenowych i architektonicznych używanych w Athlete Platform.

## Spis treści

- [Pojęcia domenowe](#pojęcia-domenowe)
- [Pojęcia architektoniczne](#pojęcia-architektoniczne)
- [Rozróżnienia krytyczne](#rozróżnienia-krytyczne)
- [Powiązane dokumenty](#powiązane-dokumenty)

## Pojęcia domenowe

### Activity

Domenowa reprezentacja wykonanej aktywności sportowej utworzona z danych źródłowych; opisuje wykonanie, a nie plan treningu.

### Activity Record

Pojedyncza próbka czasowa w `Activity`, zawierająca dostępne wartości telemetryczne dla danego timestampu.

### Adaptation

Jawna dyrektywa aplikacyjna wynikająca z oceny zawodnika, informująca politykę decyzji, czy utrzymać lub ograniczyć obciążenie; nie jest samą decyzją treningową.

### Assessment

Typowana ocena przygotowana z istniejącego kontekstu i raportów, używana przez `AdaptationPolicy`; nie jest eventem ani trwałą wiedzą.

### Athlete Memory

Append-only historia wybranych eventów zawodnika, obecnie `WORKOUT_COMPLETED`, wraz z read-side budującym typowane snapshoty; nie jest pełnym Event Sourcingiem ani Knowledge Store.

### Athlete Memory Event

Niezmienny historyczny zapis jednego obsługiwanego zdarzenia z identity, czasem wystąpienia, source identity, wersją schematu i payloadem.

### Athlete Memory Snapshot

Odtwarzalna, typowana projekcja eventów Memory z zakresu czasu `[start, end)`; jest wejściem analityki, a nie źródłem prawdy.

### Athlete State

Bieżący agregat danych potrzebnych do decyzji i planowania, złożony m.in. ze stanu health, recovery, performance i contextu.

### Body Composition Assessment

Immutable wynik `BodyCompositionEngine` zawierający aktualny profil, opcjonalny trend masy, completeness metadata, evidence, limitations, datę obowiązywania i `as_of`. Ta sama instancja jest dostępna w `IntelligenceDecisionResult` oraz `MorningCoachResult`, ale nie jest źródłem Recommendation, Explainability ani tekstu prezentacyjnego.

### Body Composition Input

Immutable, znormalizowana historia pomiarów składu ciała przygotowana w Application Layer; obecny adapter mapuje wyłącznie dostępne `HealthDaily.weight` bez dodatkowego I/O.

### Decision

Wynik polityki treningowej określający wybrany typ treningu, czas, docelowy TSS, intensywność, confidence i strukturalne powody; jedynym właścicielem decyzji jest `DecisionEngine`.

### Decision Reason

Stabilna wartość enuma opisująca strukturalną przyczynę decyzji, przeznaczona do dalszego przetwarzania bez parsowania tekstów UI.

### Evidence

Stabilna referencja do faktu lub danych źródłowych uzasadniających observation, insight albo recommendation; nie jest komunikatem prezentacyjnym.

### Execution

Analiza porównująca wykonaną `Activity` z jawnym `Workout`, w tym wykonanie bloków, czas i wynik zgodności.

### Explainability

Prezentacyjne wyjaśnienie zbudowane z gotowych decision reasons i recommendations; nie tworzy ani nie zmienia decyzji.

### Health

Bieżący stan metryk zdrowotnych przygotowany z `HealthDaily` i `HealthContext`, obecnie obejmujący obsługiwane trendy HRV, resting heart rate i snu.

### Insight

Efemeryczna, deterministyczna interpretacja jednej lub wielu observations, zawierająca typ, confidence, evidence i `as_of`; nie jest trwałą wiedzą.

### MorningCoach

Kanoniczny dzienny use case przygotowujący stan i historię zawodnika, uruchamiający Intelligence Workflow raz, planujący trening i prezentujący kompatybilny raport. `MorningCoachResult` udostępnia canonical Body Composition Assessment bez jego interpretacji przez Presenter.

### Nutrition Assessment

Immutable wynik `NutritionEngine` agregujący sekcje energii, makroskładników, fueling i hydration wraz ze statusem kompletności, completeness score, evidence, limitations, datą obowiązywania i `as_of`.

### Nutrition Input

Immutable, znormalizowany zestaw faktów przygotowany w Application Layer z dostępnych danych health oraz kanonicznego `DecisionResult`; nie wykonuje odczytów i nie zawiera wartości odgadywanych.

### Nutrition Recommendation Rule

Bezstanowa reguła globalnego Recommendation Engine mapująca dostępne cele carbohydrate i hydration z `NutritionAssessment` na istniejące `RecommendationType`; nie tworzy osobnego pipeline'u rekomendacji.

### Observation

Efemeryczna, deterministyczna projekcja datowanego faktu z health input lub Athlete Memory, zawierająca typ, wartość, confidence i evidence.

### Performance

Stan obciążenia treningowego opisany obecnie przez krótkoterminowe ATL, długoterminowe CTL, TSB oraz odpowiadające fatigue, fitness i freshness.

### Planned Workout

Wykonalna definicja treningu utworzona przez Planner z recipe i DSL, zawierająca nazwę, sport, docelowy TSS, przewidywany czas oraz bloki.

### Planner

Komponent przekształcający gotowy `DecisionResult` i `AthleteState` w `PlannedWorkout`; nie podejmuje ponownie decyzji treningowej.

### Recommendation

Immutable, pozatreningowe działanie wspierające z typem, priorytetem, confidence, evidence, source rules, stabilnym ID i `as_of`; nie zmienia treningu.

### Recommendation Context

Immutable wejście reguł Recommendation zawierające `DecisionResult`, tuple insights, tuple observations, opcjonalny `NutritionAssessment` oraz opcjonalne deterministyczne `as_of`.

### Recommendation Result

Immutable, znormalizowany i deterministycznie uporządkowany zbiór rekomendacji; pusty tuple z `as_of=None` jest poprawnym wynikiem.

### Recovery

Ocena bieżącej regeneracji zbudowana z HRV, resting heart rate i snu, zawierająca score, status, reasons oraz składowe metryki.

### Source Identity

Para `provider + external_id` identyfikująca rekord w obrębie konkretnego zewnętrznego źródła; nie jest identity zawodnika, planu, eventu ani kanonicznej Activity.

### Timeline

Uporządkowana czasowo reprezentacja bloków planu używana do dopasowania i analizy przebiegu wykonanego treningu.

### Training Prescription

Wynik etapu Prescription określający cel i parametry wymagane do selection; poprzedza finalny `DecisionResult`.

### Weekly Training Review

Typowany przegląd okresu zbudowany z trendów i wzorców tego samego `AthleteMemorySnapshot`.

### Workout

Jawny domenowy plan treningu, względem którego analizowana jest `Activity`; nie jest aktywnością wykonaną ani źródłem danych.

### WorkoutPlan

Wynik `DecisionEngine` agregujący rezultaty selection i udostępniający wybrany `DecisionResult`; nie jest jeszcze skompilowanym `PlannedWorkout`.

### WORKOUT_COMPLETED

Append-only event historyczny łączący jedną wykonaną `Activity`, jeden jawny `Workout`, source identity oraz wynik analizy post-workout.

## Pojęcia architektoniczne

### Application Layer

Warstwa orkiestrująca use case i workflow oraz przekazująca typowane dane między domeną a portami infrastruktury.

### Builder

Komponent tworzący lub normalizujący model wynikowy z gotowych danych, bez przejmowania polityki należącej do reguły lub silnika.

### Canonical Pipeline

Jedyna zaakceptowana kolejność wykonania danej zdolności; dla workflow dziennego jest to Observation → Insight → Decision → Body Composition Assessment → Nutrition Assessment → Recommendation → Explainability.

### Composition Root

Jedno jawne miejsce tworzące produkcyjny graf obiektów i łączące konkretne implementacje ze wszystkich warstw.

### Determinism

Właściwość, według której identyczne dane wejściowe dają identyczny kompletny wynik bez zależności od czasu systemowego, globalnego stanu lub kolejności nieobjętej kontraktem.

### Domain Layer

Warstwa posiadająca modele, język biznesowy i czyste reguły, niezależna od infrastruktury oraz prezentacji.

### Engine

Komponent wykonujący jedną spójną zdolność domenową lub koordynujący jej jawne etapy, bez przejmowania obowiązków sąsiednich silników.

### Body Composition Engine

Deterministyczny komponent domenowy budujący profil i trend z gotowego `BodyCompositionInput`, bez I/O, repozytorium, zegara oraz zależności od Recommendation, Explainability lub MorningCoach.

### Nutrition Engine

Deterministyczny komponent domeny Nutrition budujący `NutritionAssessment` z gotowego `NutritionInput`, bez I/O, repozytorium, zegara i zależności od MorningCoach lub Recommendation Engine.

### Infrastructure Layer

Warstwa realizująca storage, parsery, collectory, pliki, eksport i inne integracje zewnętrzne.

### Presentation Layer

Warstwa mapująca gotowe wyniki aplikacji na komunikaty, raporty, CLI i formaty wyjściowe bez zmiany decyzji domenowych.

### Projection

Model możliwy do ponownego zbudowania z danych źródłowych, używany do odczytu lub dalszej analityki, ale niebędący źródłem prawdy.

### Protocol

Mały strukturalny kontrakt Python określający wymagane zachowanie portu lub reguły bez narzucania dziedziczenia.

### Rule

Bezstanowa, deterministyczna jednostka logiki biznesowej oceniająca jawny context i zwracająca immutable wynik.

### Use Case

Operacja aplikacyjna realizująca cel użytkownika przez orkiestrację gotowych zależności.

### Workflow

Jawna sekwencja współpracujących komponentów, która nie powiela ich logiki biznesowej.

## Rozróżnienia krytyczne

| Nie mylić | Z |
|---|---|
| `Activity` | `Workout` — wykonanie nie jest planem |
| `WorkoutPlan` | `PlannedWorkout` — decyzja nie jest skompilowanym treningiem |
| Athlete Memory | Athlete Knowledge — historia nie jest trwałą interpretacją |
| Observation | Insight — projekcja faktu nie jest wnioskiem z faktów |
| Decision | Recommendation — wybór treningu nie jest działaniem wspierającym |
| Recovery result | Recovery recommendation — stan nie jest poradą |
| Source Identity | Canonical Activity Identity — rekord źródła nie rozstrzyga tożsamości sesji między providerami |
| Explainability | Decision — tekst wyjaśnia, ale nie decyduje |
| `decision.selection.SelectionEngine` | `planner.selection.SelectionEngine` — wybierają elementy na różnych etapach |

## Powiązane dokumenty

- Poprzedni: [Roadmapa](07-roadmap.md)
- Indeks: [Engineering Handbook](README.md)
- [Architektura](02-architecture.md)
- [Architecture Decision Records](03-architecture-decisions.md)
- [Source Identity](../design/source-identity.md)
