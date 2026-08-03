# 07. Roadmapa techniczna

> Stan rozwoju architektury Athlete Platform z wyraźnym rozdzieleniem elementów ukończonych, bieżących, planowanych i koncepcyjnych.

## Spis treści

- [Zasady statusu](#zasady-statusu)
- [Completed](#completed)
- [Current](#current)
- [Planned](#planned)
- [Ideas](#ideas)
- [Ryzyka i zależności](#ryzyka-i-zależności)
- [Powiązane dokumenty](#powiązane-dokumenty)

## Zasady statusu

- **Completed** oznacza, że implementacja oraz odpowiadające jej testy istnieją w bieżącym repozytorium.
- **Current** oznacza aktywną pracę dokumentacyjną lub utrzymaniową, nie ukończoną funkcję.
- **Planned** oznacza kierunek wynikający z zaakceptowanej architektury, ale bez gotowej implementacji.
- **Ideas** oznacza możliwość do oceny; nie jest zobowiązaniem ani częścią produktu.

Historyczny [Project Roadmap](../roadmap.md) opisuje wcześniejszą wizję wersji i nie jest wiarygodnym rejestrem aktualnego statusu modułów. Ten dokument nie nadaje terminów wydania.

## Completed

### Stage 1 — Core training and post-workout foundation

- ingestion `Activity` oraz parser FIT;
- decyzja i planowanie treningu;
- analiza wykonania i deterministyczny feedback;
- `PostWorkoutPipeline`.

### Stage 2 — Athlete Memory and review

- append-only event `WORKOUT_COMPLETED`;
- Memory writer, repository, reader i typed snapshot;
- training trends oraz pattern detection;
- `WeeklyReviewWorkflow` i `WeeklyTrainingReview`;
- Source Identity dla artefaktów FIT i kontrola duplikatów.

### Stage 3 — Assessment, adaptation and Athlete Intelligence

- `AthleteKnowledgeContext`, `TrainingAssessment` i `AthleteAssessment`;
- `AdaptationPolicy` oraz integracja adaptacji z decyzją;
- `ObservationProjector`, `AthleteObservation`, `InsightBuilder` i `AthleteInsight`;
- strukturalne `DecisionReason`;
- application workflow łączący intelligence z decyzją.

### Stage 4 — Recommendation Engine

- immutable modele Recommendation i context;
- bezstanowe reguły Sleep, Hydration, Recovery i Mobility;
- deterministyczny `RecommendationBuilder`;
- `RecommendationEngine` z constructor injection;
- integracja Recommendation i explainability w `IntelligenceDecisionWorkflow`;
- kompletne mapowania aktualnych `RecommendationType`.

### Stage 5 — Application Composition

- jeden composition root w `application/composition.py`;
- jawne factories Decision, Planner, Recommendation, Intelligence, Weekly Review i MorningCoach;
- constructor injection bez frameworka DI, singletonów i service locatora;
- produkcyjna konfiguracja Recommendation Rules w jednym miejscu.

### Stage 6 — MorningCoach Canonical Migration

- `MorningCoachUseCase` przygotowuje dane i wywołuje Intelligence Workflow raz;
- usunięty został bezpośredni Decision Engine z use case;
- Planner konsumuje kanoniczny `DecisionResult`;
- `MorningCoachPresenter` korzysta z kanonicznego explainability;
- jeden snapshot Memory zasila weekly review i Intelligence;
- aktywny CLI korzysta z composition root;
- legacy builders pozostają poza aktywnym pipeline'em.

### Stage 7 — Nutrition domain i canonical integration

- immutable modele `NutritionInput` i `NutritionAssessment` wraz z modelami sekcji;
- deterministyczny `NutritionEngine` dla energii, makroskładników, fueling i hydration;
- `NutritionRecommendationRule` zintegrowana z jednym globalnym Recommendation Engine;
- aplikacyjny `NutritionInputBuilder` wykorzystujący dane dostępne w canonical workflow bez dodatkowego I/O;
- `NutritionEngine` wstrzykiwany przez composition root i uruchamiany między Decision a Recommendation;
- ten sam `NutritionAssessment` jest udostępniany w `IntelligenceDecisionResult` i `RecommendationContext`;
- MorningCoach przekazuje jeden odczyt health history i zachowuje kompatybilny raport.

### Stage 8 — Body Composition

- immutable modele, deterministyczny assessment i trend masy są zaimplementowane;
- adapter in-memory i integracja z `IntelligenceDecisionWorkflow` są zaimplementowane;
- ten sam assessment jest udostępniany w `IntelligenceDecisionResult` oraz `MorningCoachResult` bez warstwy prezentacyjnej;
- Recommendation i Explainability Body Composition pozostają poza zakresem Stage 8.

### Stage 9 — Adaptive Goals

- immutable modele celu, jakości trendu i assessmentu są zaimplementowane;
- konfiguracyjny `InMemoryAthleteGoalReader` stanowi źródło MVP bez persistence i I/O;
- datowany Intelligence Workflow buduje trend quality i Goal Assessment przed jednym globalnym Recommendation Engine;
- neutralna `REVIEW_BODY_COMPOSITION_TREND` korzysta wyłącznie z kompletnego `GoalAssessment`;
- ten sam `GoalAssessment` i `BodyMassTrendQuality` są transportowane do `MorningCoachResult` bez nowej sekcji prezentacyjnej;
- ADR-009 ma status Accepted;
- trwały adapter celu, Nutrition Intake i Energy Balance nie należą do ukończonego zakresu.

### Stage 10 — Canonical Dashboard read model

- immutable, wersjonowany i datowany `AthleteDashboard` stanowi typowany read model;
- bezstanowy `DashboardEngine` składa wszystkie wymagane sekcje z gotowych wyników bez I/O i ponownego uruchamiania silników;
- composition root wstrzykuje świeży engine do `MorningCoachUseCase`, który buduje Dashboard dokładnie raz;
- MorningCoach transportuje Dashboard, zachowując dotychczasowy Presenter i `MorningCoachReport`;
- jawny `DashboardSerializer` zapewnia strict payload contract v1.0, kontrolowaną deserializację oraz snapshot/round-trip tests;
- ADR-010 ma status Accepted;
- persistence, transport HTTP/API, layout i UI nie należą do ukończonego zakresu Stage 10.

**TODO:** Repozytorium nie zawiera źródłowego dokumentu przypisującego oficjalne nazwy do Stage 1–3. Powyższe nazwy porządkują wyłącznie zaimplementowane rezultaty widoczne w kodzie i historii Git; wymagają potwierdzenia, jeśli mają stać się oficjalnymi nazwami etapów.

## Current

### Stage 11.2 — Web Experience Layer

- `web/AthleteWeb` jest głównym środowiskiem prototypowania Experience Layer i walidacji UX;
- framework-free klient Vite/TypeScript renderuje polski Morning Briefing z deterministycznych Preview Data;
- jawny `MorningBriefingPresentation` oddziela przyszły payload `AthleteDashboard v1.0` od struktury UI;
- interfejs realizuje Decision First, mobile-first responsiveness, Dark Mode i podstawy PWA bez Service Workera;
- backend, kontrakt payloadu v1.0 i zachowany klient SwiftUI pozostają bez zmian;
- mapper backendowy, API, trwały stan oraz aktywne trasy nawigacji nie należą do bieżącego zakresu.

#### Sprint 2 — Morning Briefing Polish

- uproszczono Hero Card i hierarchię nagłówka bez zmiany treści odprawy;
- zwiększono typografię, whitespace oraz rytm sekcji;
- decyzja używa jednej spokojnej linii szczegółów zamiast badge'y;
- pasek celu i lista skrótów zostały dopracowane zgodnie z wzorcami HIG;
- zakres funkcjonalny, Preview Data flow i granice backendu pozostają bez zmian.

#### Sprint 2.1 — Mobile Shell and Bottom Navigation Fix

- shell korzysta z elastycznej kolumny i pełnej dostępnej wysokości `100dvh` z fallbackiem `100vh`;
- główna zawartość wypełnia wolne miejsce bez wymuszania wysokości większej od treści;
- sticky bottom navigation pozostaje ostatnim elementem shella, respektuje safe area i nie traci sticky containment na desktopie;
- treść, modele prezentacyjne, Preview Data oraz kontrakty backendu pozostają bez zmian.

#### Sprint 3 — Morning Briefing Presentation States

- jawny discriminated union reprezentuje dokładnie stany `ready`, `partial`, `unavailable`, `stale`, `loading` i `failure`;
- warianty współdzielą shell, komponenty i tokeny, a jednocześnie transportują wyłącznie wymagane dane;
- `partial` nie formułuje twierdzeń z brakujących źródeł, `unavailable` nie pokazuje decyzji, a `stale` jawnie oznacza czas aktualizacji;
- spokojny skeleton, live regions i retry zapewniają kontrolowane zachowanie stanów przejściowych oraz błędu;
- query string umożliwia deterministyczne Preview bez panelu widocznego w produkcie;
- integracja payloadu, sieć i logika domenowa pozostają poza zakresem.

#### Sprint 3 — Visual System Alignment

- Light Mode jest głównym stylem produktu, a Dark Mode pozostaje pełnoprawnym wariantem systemowym;
- wspólne tokeny Theme rozdzielają powierzchnie neutralne od akcentów Recovery, Training, Sleep i Attention;
- hero używa lekkiego gradientu fioletowo-brzoskwiniowego, a pozostałe kolory wspierają skanowanie bez dominowania nad treścią;
- stany `partial`, `unavailable`, `stale` i `failure` otrzymują odrębne tokeny informacyjne, neutralne, ostrzegawcze i błędu bez zmiany komunikatów ani semantyki;
- struktura informacji, dane, modele prezentacyjne, nawigacja i kontrakty pozostają bez zmian.

#### Sprint 5 — AthleteDashboard Payload Mapping Boundary

- ścisły typ `AthleteDashboardPayloadV1` odwzorowuje wyłącznie publiczny wynik `DashboardSerializer` bez zależności od modeli domenowych;
- lekki runtime parser waliduje pełną strukturę, enumy, daty, timestampy, nullability i wersję kontraktu bez wyjątków jako mechanizmu przepływu;
- deterministyczny mapper rozdziela `failure` kontraktu od produktowego `unavailable` oraz mapuje kompletność i świeżość do sześciostanowej warstwy prezentacyjnej;
- `MappingContext` jawnie dostarcza czas, locale, strefę, identity i konfigurowalny próg świeżości;
- fixtures oraz `?source=payload` uruchamiają cały przepływ bez HTTP, cache i zmian backendu.

#### Sprint 5.1 — Temporal and Presentation Contract Policy

- polityka ma status Accepted i formalizuje aware timestamps jako format nowej emisji przy zachowaniu kompatybilności legacy naive w v1.0;
- `valid_for_date` ma pierwszeństwo, a jawny `MORNING_BRIEFING_MAX_AGE_MS` wynosi startowo sześć godzin;
- ownership matrix oddziela payload, client context, Preview-only data oraz kandydatów kontraktu v1.1;
- payload Preview nie przedstawia completeness jako goal achievement i nie generuje porównania bez danych;
- transport pozostaje zablokowany do czasu potwierdzenia aware emisji przez źródło produkcyjne.

### Stage 11.2 — Experience Architecture, Sprint 1

- natywny projekt `AthleteApp` dla iOS 18+ jest przygotowany w SwiftUI bez UIKit i z granicą MVVM;
- pierwszy ekran Morning Briefing korzysta wyłącznie z deterministycznych Preview Data;
- osobny model prezentacyjny chroni UI przed bezpośrednim sprzężeniem z kontraktem `AthleteDashboard`;
- współdzielone komponenty i tokeny Theme przygotowują klienta pod kolejne feature slices;
- backend, API, Apple Health i logika biznesowa pozostają poza zakresem Sprintu 1;
- build oraz uruchomienie SwiftUI Preview wymagają końcowej walidacji w pełnym Xcode 17+ z SDK iOS 18; bieżące środowisko udostępnia tylko Command Line Tools.

### Stage 11.2 — Experience Architecture, Sprint 2

- Morning Briefing ma dopracowaną hierarchię typograficzną, spokojniejszy Hero Card i większy rytm przestrzeni;
- semantyczne powierzchnie i adaptacyjne kolory zapewniają obsługę Light oraz Dark Mode;
- Dynamic Type, VoiceOver, minimalne cele dotykowe i Reduce Motion są uwzględnione w implementacji;
- subtelne animacje wejścia i postępu nie zmieniają funkcji ani danych ekranu;
- warianty Preview pokrywają wygląd domyślny, Dark Mode oraz rozmiar tekstu accessibility;
- build oraz renderowanie Preview nadal wymagają końcowej walidacji w pełnym Xcode 17+ z SDK iOS 18.

### Engineering Handbook v1.0

- ujednolicenie referencji architektonicznej, ADR-ów, standardów i strategii testowej;
- zdefiniowanie workflow pracy User–ChatGPT–Codex–Antigravity;
- przygotowanie niezależnej checklisty review;
- uporządkowanie terminologii i statusów roadmapy.

### Utrzymanie kanonicznych granic

- ochrona jedynego pipeline'u Decision → Recommendation → Explainability;
- ochrona composition root przed rozproszeniem konfiguracji;
- testy regresyjne dla MorningCoach, Source Identity i deterministyczności;
- identyfikowanie, bez niejawnego usuwania, pozostałych ścieżek compatibility/legacy.

## Planned

Poniższe obszary są udokumentowanym kierunkiem, ale nie są obecnie zaimplementowanymi modułami:

### Kontrakty historii i replay

- jawne `analysis_version` dla derived analysis `WORKOUT_COMPLETED`;
- polityka replay/re-analysis zależna od zachowania źródłowych danych;
- decyzja o archiwizacji FIT albo osobnym Activity Store.

### Athlete Knowledge i learning

- osobna decyzja architektoniczna dla Learning Engine;
- osobna decyzja o Athlete Knowledge Store;
- zachowanie rozdziału między eventem, snapshotem, insightem i trwałą wiedzą.

Nazwy te pochodzą z ADR-002/003 jako obszary przyszłe. Nie istnieją jeszcze ich runtime components ani persistence.

### Kontrolowana migracja legacy

- decyzja o deprecacji lub późniejszym usunięciu `MorningCoachBuilder` i `ExplanationBuilder`;
- redukcja bezpośredniego sprzężenia `PerformanceEngine` z `WorkoutHistoryBuilder`;
- uporządkowanie równoległych przestrzeni `planning/` i `planner/` bez zmiany publicznego API „przy okazji”.

### Stage 7.7 — dalszy zakres Nutrition

Stage 7.7 nie jest ukończony. Jego zakres wymaga osobnego promptu, implementacji i review; nie należy wnioskować o gotowych funkcjach wyłącznie z obecności canonical Nutrition Assessment.

## Ideas

Idee wymagają osobnej analizy i nie mają statusu planu:

- Canonical Activity Identity i multi-source reconciliation ponad Source Identity;
- kolejne adaptery providerów korzystające ze wspólnego `SourceIdentity`;
- dodatkowe Recommendation Rules dla istniejących typów bez aktywującej reguły, w tym limit activity;
- automatyczne testy granic importów między warstwami;
- formalny próg coverage oraz macierz wspieranych wersji Pythona;
- dedykowany workflow CI.

Nowa idea nie może zostać opisana jako funkcja produktu przed zaakceptowaniem zakresu, kontraktu i ADR-u.

## Ryzyka i zależności

| Obszar | Ryzyko | Warunek dalszej pracy |
|---|---|---|
| Knowledge/Learning | powstanie cross-cutting god object | osobny ADR i jedno źródło prawdy |
| Replay | brak pełnej telemetrii w Memory | polityka przechowywania FIT lub Activity Store |
| Legacy cleanup | przypadkowe złamanie publicznego API | call-site audit i plan deprecacji |
| Performance | hidden I/O wewnątrz engine | jawny port/snapshot oraz testy regresji |
| Nowe recommendations | zmiana zachowania użytkownika | osobna reguła, testy i mapowanie explainability |
| CI/coverage | pozorna jakość oparta na procencie | najpierw uzgodnienie bramek i krytycznych invariantów |

## Powiązane dokumenty

- Poprzedni: [Lista kontrolna review](06-review-checklist.md)
- Indeks: [Engineering Handbook](README.md)
- Następny: [Glosariusz](08-glossary.md)
- [Architektura](02-architecture.md)
- [Architecture Decision Records](03-architecture-decisions.md)
- [Historyczny Project Roadmap](../roadmap.md)
