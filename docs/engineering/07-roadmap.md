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

### Stage 10 — Athlete Dashboard Core & Multi-state Presentation

- sześciowariantowe `AthleteDashboardState` reprezentuje stany `ready`, `partial`, `unavailable`, `stale`, `loading` i `failure`;
- `DashboardSerializer` eksportuje bezstanowy kontrakt v1.0 dla interfejsów klientów;
- `AthleteDashboardMapper` mapuje payload na typed presentation model;
- widok AthleteWeb wspiera stany dynamiczne, Preview Mode oraz dynamiczne motywy (Light / Dark Mode).

### Stage 20 — Morning Briefing Subsystem

- deterministyczny `MorningBriefingBuilder` oraz `MorningRecommendationEngine`;
- stabilna warstwa serializacji `MorningBriefingSerializer` i kontrakt HTTP API `GET /api/v1/morning-briefing`;
- testowalny `MorningBriefingInputProvider` oraz bezpieczna obsługa błędów 503;
- kompaktowa karta Dashboard Card oraz pełnoekranowy widok Morning Briefing w AthleteWeb.

### Stage 21 — Performance Lab Subsystem

- **Domain Foundation (21.1):** czyste, zamrożone modele `PerformanceStage`, `PerformanceTestSession`, `PerformanceThreshold`, `PerformanceAssessment` oraz typowane Enumy (`PerformanceTestType`, `PerformanceTestStatus`, `ExerciseModality`, `StageCompletionStatus`) z walidacją inwariantów;
- **Session & Stage Builder (21.2):** bezstanowy `PerformanceTestSessionBuilder` oraz zamrożone modele wejściowe (`PerformanceStageInput`, `PerformanceTestSessionInput`) bez niejawnych konwersji i z zachowaniem kolejności;
- **Lactate Curve Engine (21.3):** bezstanowy `LactateCurveBuilder` budujący `LactateCurve` wyłącznie z ukończonych etapów posiadających stężenie mleczanów, wraz z wyliczaniem zmian bezwzględnych i względnych bez interpolacji;
- **Threshold Analysis LT1 / LT2 (21.4):** deterministyczny `LactateThresholdAnalyzer` realizujący metodę stałego stężenia mleczanu (`fixed_2_mmol` dla LT1, `fixed_4_mmol` dla LT2) ze zdefiniowanymi statusami `DETECTED`, `NOT_REACHED`, `INSUFFICIENT_DATA`;
- **Test History Read Model (21.5):** bezstanowy `PerformanceTestHistoryBuilder` deduplikujący sesje po `test_id` (wybór najnowszej), sortujący chronologicznie `oldest -> newest` oraz ograniczający analizę mleczanową wyłącznie do `LACTATE_STEP_TEST`;
- **Serialization & HTTP API (21.6 / 21.6A):** `PerformanceTestHistorySerializer`, provider boundary `PerformanceTestSessionProvider` i endpoint `GET /api/v1/performance-lab/history` z utwardzonym kontraktem JSON-safe i bezpieczną obsługą 503;
- **AthleteWeb Performance Experience (21.7 / 21.7A):** typowany `PerformanceLabApiClient` z pełną walidacją runtime, responsywne widoki historii i szczegółów testu, lekki wykres SVG krzywej mleczanowej bez interpolacji oraz bezprzeładowaniowy routing.

### Stage 22 — Decision Intelligence 2.0 Subsystem

- **Athlete Decision Context (22.1 / 22.1A):** neutralny, zamrożony kontrakt `AthleteDecisionContext` zbierający snapshoty `recovery`, `training`, `biomarkers` i `performance` ze ścisłymi inwariantami i walidacją `ContextDataStatus`;
- **Context Composition Layer (22.2):** bezstanowy `AthleteDecisionContextBuilder` składający cztery snapshoty oraz provider boundary `AthleteDecisionContextProvider`;
- **Deterministic Decision Policy V2 (22.3):** bezstanowy ewaluator `DecisionPolicyV2` oceniający kontekst i realizujący 10 jawnych reguł w deterministycznej kolejności źródeł, rozstrzygający konflikty według hierarchii akcji (`REST` > `REVIEW` > `REPLACE_WITH_RECOVERY` > `REDUCE` > `PROCEED`) i wyznaczający pewność (`LOW` -> 0.60, `CRITICAL` -> 0.95);
- **Recommendation Plan & Explainability (22.4):** bezstanowy `RecommendationPlanBuilder` mapujący wynik polityki na `RecommendationPlan` (z jedną rekomendacją główną oraz rekomendacjami dodatkowymi) i `DecisionExplanation` odzwierciedlający wszystkie sygnały bez utraty danych;
- **Decision History & Audit (22.5 / 22.5A):** immutable `DecisionAuditRecord` i read model `DecisionHistory` z bezstanowymi builderami sortującymi chronologicznie `oldest -> newest` i deduplikującymi po `decision_id` z rozstrzyganiem remisów po `recorded_at`;
- **Serialization & HTTP API (22.6 / 22.6A):** `DecisionAuditRecordSerializer`, provider boundary `DecisionAuditRecordProvider` oraz endpoint `GET /api/v1/decision-intelligence/latest` serwujący gotowy rekord (z obsługą `decision: null` i bezpiecznym błędem 503);
- **AthleteWeb AI Coach Experience (22.7 / 22.7A):** typowany `DecisionIntelligenceApiClient` z pełną walidacją runtime, responsywny widok AI Coach prezentujący kartę Hero, rekomendacje, wyjaśnienia oraz 4 źródła kontekstu z bezprzeładowaniowym routingiem.

### Stage 23 — Decision Runtime & Persistence

- **Decision Execution Orchestrator (23.1):** bezstanowy `DecisionExecutionService` wywołujący kompletny pipeline Decision Intelligence 2.0;
- **Real Decision Context Adapters (23.2 / 23.2A):** neutralne adaptery `Recovery`, `Training`, `Biomarkers`, `Performance` oraz composite provider `RuntimeAthleteDecisionContextProvider` z gwarancją pojedynczego pobrania `MorningBriefingInput`;
- **Runtime Workflow & Composition (23.3):** czysty workflow `DecisionRuntimeWorkflow` ze wstrzykiwalnym zegarem `SystemUtcDecisionClock` i generatorem ID `UuidDecisionIdGenerator`;
- **DuckDB Decision Repository (23.4 / 23.4A):** trwałe, wątkowo bezpieczne repozytorium `DuckDbDecisionAuditRecordRepository` z obsługą unikalnych transakcji append-only oraz weryfikacją spójności metadanych;
- **Persisted Runtime Workflow & Latest Provider (23.5 / 23.5A):** dekorator `PersistedDecisionRuntimeWorkflow`, `RepositoryDecisionAuditRecordProvider`, produktywny WSGI composition root w `server/app.py` oraz CLI runner `scripts/run_decision_runtime.py`;
- **Decision History HTTP API (23.6):** `RepositoryDecisionHistoryProvider`, bezstanowy `DecisionHistorySerializer` oraz endpoint `GET /api/v1/decision-intelligence/history` zwracający rekordy chronologicznie (*oldest $\rightarrow$ newest*);
- **AthleteWeb Decision History Experience (23.7 / 23.7A):** niezależny interfejs historii `DecisionHistoryContainer` z odwróconą prezentacją (*newest $\rightarrow$ oldest*), dostępnymi szczegółami kart, polską lokalizacją etykiet oraz w pełni izolowanym cyklem życia zapytań HTTP.


## Planned


Poniższe obszary są udokumentowanym kierunkiem, ale nie są obecnie zaimplementowanymi modułami:

### Kontraktor historii i replay

- jawne `analysis_version` dla derived analysis `WORKOUT_COMPLETED`;
- polityka replay/re-analysis zależna od zachowania źródłowych danych;
- decyzja o archiwizacji FIT albo osobnym Activity Store.

### Athlete Knowledge i learning

- osobna decyzja architektoniczna dla Learning Engine;
- osobna decyzja o Athlete Knowledge Store;
- zachowanie rozdziału między eventem, snapshotem, insightem i trwałą wiedzą.

## Ideas

Idee wymagają osobnej analizy i nie mają statusu planu:

- Canonical Activity Identity i multi-source reconciliation ponad Source Identity;
- kolejne adaptery providerów korzystające ze wspólnego `SourceIdentity`;
- dodatkowe Recommendation Rules dla istniejących typów bez aktywującej reguły, w tym limit activity;
- automatyczne testy granic importów między warstwami;
- formalny próg coverage oraz macierz wspieranych wersji Pythona;
- dedykowany workflow CI.

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
