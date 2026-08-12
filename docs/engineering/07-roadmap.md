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

### Stage 24 — Production Decision Data Integration

- **Production Morning Briefing Boundary (24.1 / 24.1A):** `ProductionMorningBriefingInputProvider` zasilający kontekst z gotowego `MorningCoachResult` i `BiomarkersDashboard`;
- **Performance Read-Model Boundary (24.2):** eliminacja powielonej analizy mleczanowej w Decision Intelligence poprzez konsumpcję gotowego read-modelu `PerformanceTestHistory`;
- **Recovery Context Enrichment (24.3):** uzupełnienie kontekstu regeneracji o statusy `hrv_status`, `resting_heart_rate_status` oraz `sleep_status` bezpośrednio z `RecoveryEngine`;
- **Training Context Enrichment (24.4):** zasilenie kontekstu treningowego kanonicznym `planned_session_type`, `planned_intensity`, `recent_training_load` i `fatigue_status`;
- **Biomarker Context Enrichment (24.5):** zastąpienie syntetycznego podsumowania realnymi sygnałami z `BiomarkersDashboard` i precyzyjnym podliczeniem `critical_count` wyłącznie dla flag laboratoryjnych;
- **Production Composition Root & Real Data Runtime (24.6 / 24.6A):** `ProductionDecisionRuntimeContainer`, poprawnie rozwiązana canonical path `<repo>/data/database/decisions.duckdb` oraz obsługa cyklu życia zasobów;
- **AthleteWeb Real-Data Verification (24.7):** bezkompromisowa walidacja odczytowa interfejsu AI Coach z trwałym backendem bez modyfikacji danych na serwerze;
- **Final Verification & Stage 24 Closure (24.8):** formalne zamknięcie etapu z pełnym audytem spójności architektonicznej i regresyjnej.


### Stage 25 — Automated Daily Runtime

- **Crash-Safe Daily Ledger & Coordinator (25.1):** wprowadzono model ledgeru `daily_decision_executions`, wyliczanie `calculate_local_run_date` dla strefy zawodnika (`Europe/Warsaw`) oraz koordynator `DailyDecisionRuntimeCoordinator` z gwarancją ścisłego `at-most-once` wywołania na dzień;
- **Concurrency & CAS Hardening (25.1A):** wyeliminowano deadlock samobójczy, utwardzono atomowość zapytań SQL (`UPDATE ... RETURNING`) oraz przetestowano wyścigi wątków i odrzucanie spóźnionych próbek workerów (`stale worker CAS conflict`);
- **Daily Production CLI & Composition (25.2):** udostępniono produkcyjny punkt wejścia CLI `scripts/run_daily_decision_runtime` z bezpiecznym loggingiem operacyjnym (bez wycieku danych zdrowotnych) i stabilnym kontraktem kodów wyjścia (0 dla sukcesów/skips, 1 dla awarii);
- **macOS LaunchAgent & Operations Automation (25.3):** zaimplementowano repozytoryjny szablon plist, skrypty instalatora/odinstalowywacza (`ops/macos/`) ze wsparciem dla target-override w środowiskach z ograniczonymi uprawnieniami, harmonogramem `StartCalendarInterval`, `RunAtLoad` dla uruchomienia po załadowaniu agenta oraz dokumentacją operacyjną. Realny bootstrap, RunAtLoad i idempotency smoke zostały zweryfikowane; trwała instalacja w standardowym `~/Library/LaunchAgents` na bieżącym zarządzanym Macu pozostaje zablokowana przez uprawnienia środowiska.

### Stage 26 — Adaptive Training Plan

- **Domain Model & Calendar Contract (26.1):** utworzono nową czystą domenę `training_plan/` wprowadzającą niezmienne modele `PlannedSessionKind` (`TRAINING`, `REST`), `PlannedSession` (wielodniowe zamiary z walidacją inwariantów i kanonicznym `target_tss=0.0` dla dni REST), `TrainingPlan` (z gwarancją kompletnego 1-slot-per-day pokrycia zakresu dat) oraz bezstanowy pomocnik `TrainingPlanSessionSelector` i protokół `TrainingPlanProvider`. Domena nie posiada żadnych zależności od podsystemów decyzyjnych ani generowania workoutów;
- **Baseline Weekly Plan Builder (26.2):** wprowadzono bezstanowe modele szablonu tygodniowego `Weekday` (dopasowany do `date.weekday()`), `WeeklySessionIntent`, `TrainingIntent` (wymagający dokładnie 7 slotów i zapisu chronologicznego Monday->Sunday) oraz bezstanowy projektor `BaselineTrainingPlanBuilder` budujący kanoniczne `TrainingPlan` z deterministyczną identyfikacją sesji `{plan_id}:{YYYY-MM-DD}` na dowolnym zakreślonym przedziale kalendarzowym;
- **Daily Adaptive Reconciliation (26.3):** zaimplementowano bezstanowy podsystem uzgadniania `DailyTrainingReconciler` w warstwie aplikacji oraz domeny wyjściowej `PrescriptionDisposition` (`AS_PLANNED`, `REDUCED`, `RECOVERY_REPLACEMENT`, `REST`, `HOLD_FOR_REVIEW`) i niezmiennego preskrypcji `FinalSessionPrescription`. Uzgadnianie konsumuje utrwalony rekord `DecisionAuditRecord`, stosuje nakładkę preskrypcyjną bez modyfikacji planu bazowego, nakłada zamrożony współczynnik redukcji V1 = 0.70, limity regeneracji (max 45 min) oraz bezwzględny zakaz eskalacji zaplanowanych dni odpoczynku REST do treningów;
- **Training Plan Persistence, History & Read API (26.4):** zaimplementowano dedykowaną bazę danych `data/database/training_plan.duckdb`, repozytoria DuckDB (`DuckDbTrainingPlanRepository`, `DuckDbFinalSessionPrescriptionRepository`) ze ścisłą semantyką zapisu append-only (no-op przy identycznym payloadzie, `TrainingPlanConflictError` przy próbie nadpisania), kanoniczne kodeki JSON, bezstanowe serializatory oraz 4 odczytowe punkty końcowe HTTP GET (`/api/v1/training-plan/latest`, `/history`, `/prescriptions/latest`, `/prescriptions/history`). Zapytania odczytowe w 100% konsumują stan utrwalony bez wywoływania generatorów ani przeliczania decyzji;
- **Production Adaptive Daily Runtime & Stage Closure (26.5):** połączono zintegrowany cykl `Stage 26 Adaptive Training Plan` z automatycznym dziennym środowiskiem wykonawczym `Stage 25 Daily Decision Runtime`. Wprowadzono provenance `plan_id` i `planned_session_id` w `TrainingDecisionContext`, bezstanowy `TrainingPlanDecisionContextAdapter`, wyczyszczono twardo zakodowane harmonogramy osobiste, zaimplementowano koordynator `AdaptiveDailyRuntimeCoordinator` wspierający at-most-once execution, idempotencję oraz crash recovery po odzyskaniu wykonania, zaktualizowano produkcyjne composition root `create_production_adaptive_daily_runtime` i udostępniono flagę CLI `--training-plan-db`. Stage 26 = 100% ukończony.

### Stage 27 — Production Runtime & Reliability

- **Runtime Audit & Contract (27.1):** zinwentaryzowano produkcyjne punkty wejścia, cztery magazyny DuckDB, zależności kolejności, gwarancje idempotencji, ryzyka blokad, semantykę czasu i zachowanie po awarii. Potwierdzono, że bieżący harmonogram koordynuje tylko Decision Intelligence oraz Final Session Prescription, a nie cały przepływ ingestion -> facts -> assessment -> decision -> plan/prescription -> briefing -> read models. Docelowy cienki `ProductionDailyRuntime`, immutable kontrakt wyniku/audytu i plan migracji opisuje [Production Runtime and Reliability Contract](09-production-runtime.md).
- **Runtime Contract & Audit Persistence (27.2):** zaimplementowano dedykowany bounded package `production_runtime/`, zamrożony kontrakt próby runtime w wersji `1.0`, jawne statusy i fazy, operacyjne warning/failure, generyczne source watermarks, zegar UTC i pojedynczą granicę wyznaczania daty Europe/Warsaw. Dedykowany `production_runtime.duckdb` przechowuje append-only rewizje wielu prób dla jednego dnia z CAS, idempotentnym no-op identycznej rewizji, konfliktami payloadu oraz pełną rekonstrukcją kontraktu. Nie zaimplementowano jeszcze koordynatora ani wykonywania faz.
- **Idempotent Ingestion & Activity Fact Synchronization (27.3):** wyodrębniono bez duplikowania logiki istniejące standardowe operacje FIT do aplikacyjnych serwisów zapisu `workouts` i naprawy `ACTIVITY_RECORDED`, dodano kanoniczne ścieżki health/FIT oraz jednoznaczny ownership połączenia. Ograniczony `IngestionRuntimeSlice` zapisuje RUNNING przed pracą, osobną rewizję INGESTION i terminalną rewizję PARTIAL po synchronizacji faktów, obsługuje jawny resume po `runtime_id`, zachowuje SHA-256 `fit_file` identity, raportuje rzeczywiste liczniki/watermarks i klasyfikuje ograniczone awarie. Pełny runtime pozostaje niezaimplementowany; Stage 27 = 50%.
- **Runtime State, Health & Diagnostics (27.4):** dodano wyłącznie odczytowy `RuntimeOperationalStatusReader` i operator-friendly snapshot bez kopiowania kontraktu persistence, klasyfikacje health/stale/resumability, kanonicznie uporządkowane diagnostyki faz z uczciwym `NOT RUN`, ostatni trwały postęp oraz wszystkie istniejące warnings, failures, watermarks, counters i references. Repozytorium audytu otrzymało jawny tryb DuckDB `read_only`, a `python -m scripts.runtime_status` obsługuje latest/date/all-attempts/runtime-id bez tworzenia bazy lub rewizji. HTTP został świadomie odroczony; Stage 27 = 65%.
- **Authoritative Daily Runtime Coordinator (27.5):** wdrożono cienki `ProductionDailyRuntime` z ośmioma adapterami faz, rewizją po każdej trwałej granicy, ścisłym inwariantem COMPLETED i ograniczonym resume. Assessment, Decision i dowód Morning Briefing współdzielą jeden zamrożony snapshot; publikacja wyłącznie waliduje repozytoria. Brak planu jest stabilnym błędem, reconciliation nie interpretuje faktów jako wykonania, a nowy CLI pozostaje kandydatem. Scheduler i LaunchAgent nie zostały przełączone; Stage 27 = 80%.
- **Persistent Assessment Snapshot & Recovery Certification (27.6):** minimalny `MorningBriefingInput` używany przez runtime jest utrwalany append-only w `production_runtime.duckdb` jako `assessment:sha256:<digest>`, z kanonicznym kodekiem, kontrolą integralności i idempotentnym odtworzeniem providera. Resume obejmuje wszystkie późne granice faz, publikacja weryfikuje snapshot, a izolowane fixtures certyfikują pełny cykl, brak duplikatów i missing-plan. Scheduler pozostaje bez zmian; Stage 27 = 90%.
- **Production Cutover Preparation (27.7 Gate A):** przygotowano deterministyczny tryb scheduler, read-only preflight, izolowaną certyfikację legacy-vs-candidate, produkcyjny i rollbackowy szablon LaunchAgent oraz runbook Gate B. Gate B nie został wykonany; Stage 27 pozostaje 90% i nie jest zamknięty.

## Planned

### Stage 27 — Production Runtime & Reliability

- Sprint 27.7 Gate B: ręczny cutover trwałego backendu schedulera (preferowany
  LaunchAgent, user cron jako fallback dla zarządzanego Maca), pierwszy live runtime,
  weryfikacja HEALTHY/NO_ACTION i dopiero wtedy decyzja o 100% CLOSED.


Poniższe obszary są udokumentowanym kierunkiem, ale nie są obecnie zaimplementowanymi modułami:

### Stage 25 — Automated Daily Runtime

- automatyczne wyzwalanie Decision Runtime w cyklu dziennym bez konieczności rącznego wywołania CLI;
- powiadomienia i subskrypcje wyników rekomendacji.

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
