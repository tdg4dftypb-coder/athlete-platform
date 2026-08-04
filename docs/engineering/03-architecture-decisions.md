# 03. Architecture Decision Records

> Rejestr zaakceptowanych decyzji architektonicznych Athlete Platform i ich konsekwencji dla implementacji.

## Spis treści

- [Zasady rejestru](#zasady-rejestru)
- [ADR-001 — Modularny monolit i jawne granice](#adr-001---modularny-monolit-i-jawne-granice)
- [ADR-002 — Ukończenie treningu i Athlete Memory](#adr-002---ukończenie-treningu-i-athlete-memory)
- [ADR-003 — Athlete Intelligence](#adr-003---athlete-intelligence)
- [ADR-004 — Recommendation Engine](#adr-004---recommendation-engine)
- [ADR-005 — Jawny composition root](#adr-005---jawny-composition-root)
- [ADR-006 — Kanoniczny MorningCoach](#adr-006---kanoniczny-morningcoach)
- [ADR-007 — Kanoniczna integracja Nutrition](#adr-007---kanoniczna-integracja-nutrition)
- [ADR-008 — Body Composition Assessment](#adr-008---body-composition-assessment)
- [ADR-009 — Adaptive Goals](#adr-009---adaptive-goals)
- [ADR-010 — Kanoniczny Athlete Dashboard Read Model](#adr-010---kanoniczny-athlete-dashboard-read-model)
- [Rejestr ADR](#rejestr-adr)
- [Powiązane dokumenty](#powiązane-dokumenty)

## Zasady rejestru

Ten dokument konsoliduje decyzje utrwalone w kodzie, historii projektu oraz źródłowych ADR-ach. Nie rozszerza architektury opisanej w [referencji architektonicznej](02-architecture.md).

Statusy:

- **Accepted** — decyzja obowiązuje;
- **Superseded** — decyzja została zastąpiona przez wskazany ADR;
- **Deprecated** — rozwiązanie jest zachowane tylko dla kompatybilności;
- **Proposed** — propozycja nie jest jeszcze wiążąca.

Zmiana odpowiedzialności silnika, publicznego kontraktu, źródła prawdy lub kierunku zależności wymaga aktualizacji istniejącego ADR albo nowego rekordu. Korekta implementacyjna, która nie zmienia decyzji, nie wymaga osobnego ADR.

## ADR-001 — Modularny monolit i jawne granice

### Status

**Accepted**

### Context

Platforma obejmuje ingestion danych, zdrowie, regenerację, planowanie, analizę wykonania, pamięć zawodnika, decyzje i prezentację. Jeden globalny silnik mieszałby reguły domenowe, orkiestrację, I/O oraz rendering i utrudniał niezależne testowanie.

### Decision

Athlete Platform jest rozwijana jako modularny monolit z logicznymi warstwami Domain, Application, Infrastructure i Presentation.

- logika domenowa używa typowanych wejść i wyników;
- use case oraz workflow odpowiadają za kolejność wywołań;
- I/O pozostaje na granicach infrastrukturalnych;
- prezentacja nie jest źródłem decyzji;
- composition root jest kontrolowanym miejscem, które zna konkretne implementacje;
- nowe moduły nie zależą od elementów legacy bez jawnej decyzji.

Fizyczne katalogi nie są idealnym odwzorowaniem warstw. Granice obowiązują semantycznie i są rozwijane przyrostowo.

### Consequences

- komponenty można testować bez uruchamiania całej aplikacji;
- zależności i odstępstwa są widoczne;
- migracje starszych ścieżek mogą odbywać się etapami;
- composition root zależy od wielu modułów, ale zależność nie może być odwrócona;
- istniejące sprzężenia legacy, np. w Performance, wymagają jawnego traktowania jako długu technicznego.

### Alternatives considered

- **Mikroserwisy** — odrzucone; aktualna skala nie uzasadnia kosztu operacyjnego i kontraktów sieciowych.
- **Jeden globalny Platform Engine** — odrzucone jako docelowy wzorzec; skupiałby zbyt wiele odpowiedzialności.
- **Warstwy wyłącznie według katalogów** — odrzucone na czas migracji, ponieważ nie odpowiadają stanowi istniejącego repozytorium.

## ADR-002 — Ukończenie treningu i Athlete Memory

### Status

**Accepted**

Źródło: [ADR-002 — Workout Completion Architecture](../adr/002-workout-completion-architecture.md).

### Context

Platforma analizuje wykonaną `Activity` względem jawnego `Workout`. Potrzebuje niezmiennej historii ukończonych treningów, ale nie pełnego Event Sourcingu ani trwałego magazynu interpretacji o zawodniku.

### Decision

- `PostWorkoutRecordingService` uruchamia `PostWorkoutPipeline`, a następnie zapisuje event `WORKOUT_COMPLETED` przez `AthleteMemoryWriter`.
- Jeden event dotyczy dokładnie jednej `Activity` i jednego jawnego `Workout`.
- Event jest append-only, ma `schema_version`, metadata źródła i payload.
- Source Identity to para `provider + external_id`; dla pliku FIT identyfikator jest SHA-256 surowych bajtów.
- `AthleteMemoryReader` i `AthleteMemorySnapshot` są projekcjami read-side, nie źródłem prawdy.
- Source facts, derived analysis i presentation mają różne znaczenie, nawet jeśli obecny payload przechowuje je razem.
- Pełna telemetria FIT nie jest przechowywana w Athlete Memory.

### Consequences

- historia wykonanych sesji jest audytowalna i odporna na zmianę bieżących reguł;
- ten sam artefakt źródłowy można odrzucić jako duplikat;
- snapshot i analitykę można przebudowywać;
- pełny replay analizy blokowej wymaga zachowanego źródła albo osobnego Activity Store;
- historyczna derived analysis nie jest trwałą wiedzą o zawodniku.

### Alternatives considered

- **Zapisywanie tylko derived results** — odrzucone, bo traci source facts.
- **Przechowywanie pełnej telemetrii w evencie** — odrzucone; Athlete Memory nie jest magazynem szeregów czasowych.
- **Automatyczne odgadywanie planu z aktywności** — odrzucone; plan musi być jawny.
- **Pełny Event Sourcing całej aplikacji** — nie został przyjęty.

## ADR-003 — Athlete Intelligence

### Status

**Accepted**

Źródło: [ADR-003 — Athlete Intelligence](../adr/ADR-003-athlete-intelligence.md).

### Context

Eventy i snapshot Memory nie powinny być bezpośrednio interpretowane przez politykę decyzji. Potrzebna jest mała, deterministyczna warstwa opisująca obserwowane zachowania bez utrwalania ich jako wiedzy.

### Decision

Przyjęto przepływ:

```text
HealthObservationInput + AthleteMemorySnapshot
→ ObservationProjector
→ AthleteObservation
→ InsightBuilder
→ AthleteInsight
→ DecisionEngine
```

- observations i insights są efemerycznymi, immutable projekcjami;
- zachowują confidence, evidence i datę wynikającą ze źródła;
- nie zawierają tekstów UI;
- projector i builder nie zapisują danych ani nie korzystają z infrastruktury;
- `DecisionEngine` otrzymuje przygotowane insighty, a nie repository lub Athlete Memory.

### Consequences

- historia, interpretacja i decyzja pozostają rozdzielone;
- wyniki mogą zostać przeliczone deterministycznie;
- reguły intelligence mogą być testowane na danych w pamięci;
- Knowledge Store i Knowledge Engine nie są wymagane przez bieżący pipeline.

### Alternatives considered

- **Bezpośredni dostęp Decision Engine do Memory** — odrzucone z powodu sprzężenia z historią i I/O.
- **Persistowanie każdego insightu** — odrzucone; insight jest bieżącą projekcją, nie źródłem prawdy.
- **LLM jako generator faktów** — odrzucone; model generatywny nie jest źródłem prawdy.

## ADR-004 — Recommendation Engine

### Status

**Accepted**

Decyzja jest utrwalona przez pakiet `recommendation/`, testy oraz integrację w `IntelligenceDecisionWorkflow`. Osobny źródłowy plik ADR-004 nie istnieje w repozytorium.

### Context

`DecisionEngine` wybiera trening, ale sportowiec może potrzebować także działań wspierających: snu, nawodnienia, mobility lub regeneracji. Umieszczenie tych działań w Decision Engine mieszałoby decyzję treningową z poradami pozatreningowymi.

### Decision

- `DecisionEngine` pozostaje jedynym właścicielem decyzji treningowej.
- `RecommendationRule` analizuje wyłącznie `RecommendationContext` i zwraca `tuple[Recommendation, ...]`.
- `RecommendationContext` zawiera `DecisionResult`, insights, observations, opcjonalne `NutritionAssessment`, opcjonalne `GoalAssessment` i opcjonalne deterministyczne `as_of`.
- `RecommendationEngine` tylko uruchamia wstrzyknięte reguły i przekazuje kandydatów do buildera.
- `RecommendationBuilder` deduplikuje po typie, normalizuje, generuje stabilne ID i sortuje wynik.
- modele Recommendation są immutable i nie zawierają tekstów UI.
- teksty powstają dopiero w `DecisionExplainabilityBuilder`.
- aktywny zestaw reguł jest jawnie konfigurowany w composition root.

### Consequences

- nowe reguły można dodawać bez zmiany Decision Engine;
- kolejność reguł nie wpływa na wynik końcowy;
- reguły nie wykonują I/O i są łatwe do testowania;
- rekomendacja nie może po cichu zmienić treningu;
- kompletność mapowań prezentacyjnych musi być walidowana.

### Alternatives considered

- **Rekomendacje wewnątrz Decision Engine** — odrzucone; narusza jedną odpowiedzialność i jedyne źródło decyzji.
- **Logika reguł w builderze** — odrzucone; builder tylko normalizuje gotowych kandydatów.
- **Globalny Rule Registry** — odrzucone na obecnym etapie; konfiguracja jest jawna.
- **Losowe UUID lub `hash()`** — odrzucone dla wynikowego ID; nie zapewniają odtwarzalności.

## ADR-005 — Jawny composition root

### Status

**Accepted**

Decyzję implementuje `application/composition.py`.

### Context

Tworzenie Decision, Recommendation, Planner i workflow było rozproszone. Utrudniało to kontrolę nad aktywną konfiguracją, testowanie i migrację MorningCoach.

### Decision

- produkcyjny graf zależności jest składany przez małe funkcje `build_*()` w jednym module;
- zależności są przekazywane przez konstruktory;
- fabryki zwracają świeże instancje;
- nie używa się frameworka DI, singletonów, service locatora ani import-time instancji usług;
- reguły Recommendation są konfigurowane jawną tuple;
- budowanie grafu nie powinno wykonywać logiki biznesowej ani odczytu danych.

### Consequences

- aktywna konfiguracja aplikacji jest widoczna w jednym miejscu;
- testy mogą wstrzykiwać fakes i spies;
- entry pointy są cienkie;
- composition root zna wszystkie potrzebne konkrety i jest kontrolowanym wyjątkiem od zwykłego kierunku zależności;
- część konstruktorów domyślnych pozostaje czasowo dla kompatybilności.

### Alternatives considered

- **Framework DI** — odrzucony jako niepotrzebna złożoność.
- **Singletony lub globalny kontener** — odrzucone z powodu ukrytego stanu.
- **Tworzenie silników w use case/workflow** — odrzucone; miesza konfigurację z wykonaniem.
- **Konfiguracja w każdym skrypcie** — odrzucona; prowadzi do rozbieżnych pipeline'ów.

## ADR-006 — Kanoniczny MorningCoach

### Status

**Accepted**

Decyzję implementują `MorningCoachUseCase`, `MorningCoachPresenter` oraz composition root.

### Context

MorningCoach posiadał alternatywną ścieżkę decyzyjną i explainability. Po integracji Recommendation Engine utrzymywanie dwóch pipeline'ów groziło inną decyzją, innymi rekomendacjami i rozbieżnym raportem.

### Decision

- `MorningCoachUseCase` przygotowuje `AthleteState`, health input, jeden snapshot Memory, weekly review, assessments i adaptation;
- `IntelligenceDecisionWorkflow.run()` jest jedyną kanoniczną ścieżką Decision → Recommendation → Explainability i jest wywoływany raz;
- Planner otrzymuje kanoniczny `DecisionResult` z `IntelligenceDecisionResult`;
- `MorningCoachPresenter` adaptuje gotowe wyniki do kompatybilnego `MorningCoachReport`;
- use case nie otrzymuje i nie wywołuje `DecisionEngine`, `RecommendationEngine` ani explainability buildera bezpośrednio;
- legacy `MorningCoachBuilder` i `ExplanationBuilder` pozostają publiczne, ale poza aktywną ścieżką.

### Consequences

- MorningCoach nie może ominąć Recommendation Engine ani kanonicznego explainability;
- jeden snapshot zasila weekly review i Intelligence;
- publiczny raport pozostaje kompatybilny;
- starsze builders wymagają późniejszej, osobnej decyzji o deprecacji lub usunięciu.

### Alternatives considered

- **Pozostawienie bezpośredniego Decision Engine w MorningCoach** — odrzucone jako drugi pipeline.
- **Uruchamianie Recommendation Engine w Presenterze** — odrzucone; prezentacja nie wykonuje logiki domenowej.
- **Natychmiastowe usunięcie legacy API** — odrzucone ze względu na kompatybilność.

## ADR-007 — Kanoniczna integracja Nutrition

### Status

**Accepted**

Decyzję implementują `NutritionInputBuilder`, `NutritionEngine`, `IntelligenceDecisionWorkflow` oraz globalny Recommendation Engine skonfigurowany w composition root.

### Context

Nutrition Assessment korzysta z dostępnych faktów health i kanonicznej decyzji treningowej. Osobny pipeline rekomendacji nutrition albo bezpośrednie uruchamianie Nutrition w MorningCoach tworzyłoby konkurencyjne źródło rekomendacji, dodatkowe odczyty danych i niespójne explainability.

### Decision

- aplikacyjny `NutritionInputBuilder` normalizuje wyłącznie dane już załadowane przez MorningCoach oraz kanoniczny `DecisionResult`;
- adapter nie wykonuje I/O, nie używa zegara i nie uzupełnia braków fikcyjnymi wartościami;
- `IntelligenceDecisionWorkflow` uruchamia wstrzyknięty `NutritionEngine` po Decision Engine i przed Recommendation Engine;
- dokładnie ten sam `NutritionAssessment` trafia do `RecommendationContext` oraz `IntelligenceDecisionResult`;
- jeden globalny Recommendation Engine uruchamia `NutritionRecommendationRule` razem z pozostałymi regułami i normalizuje duplikaty według `Recommendation.type`;
- MorningCoach odczytuje health history raz, nie zna Nutrition Engine i korzysta z kanonicznego explainability.

Kanoniczna sekwencja integracji to:

```text
NutritionInput
→ NutritionEngine
→ NutritionAssessment
→ NutritionRecommendationRule
→ globalny RecommendationEngine
```

### Consequences

- nutrition recommendations uczestniczą w jednym wyniku i jednym explainability pipeline;
- brak danych prowadzi do partial lub insufficient assessment zgodnie z kontraktem Nutrition Engine;
- nie istnieje drugi Nutrition Recommendation Engine;
- builder globalnych rekomendacji deduplikuje nakładające się działania, w tym hydration;
- Presenter nie interpretuje Nutrition Assessment i zachowuje dotychczasowy kontrakt raportu.

### Alternatives considered

- **Osobny Nutrition Recommendation Engine** — odrzucony jako duplikacja istniejącego mechanizmu.
- **Uruchamianie Nutrition Engine w MorningCoach** — odrzucone; use case nie powinien interpretować assessmentu ani znać silnika domenowego.
- **Budowanie NutritionInput w domenie lub Presenterze** — odrzucone; normalizacja danych dostępnych w workflow należy do Application Layer.
- **Drugi odczyt Health Repository** — odrzucony z powodu ukrytego I/O i ryzyka niespójnych snapshotów danych.

## ADR-008 — Body Composition Assessment

### Status

**Accepted**

### Context

Body Composition wymaga deterministycznej oceny aktualnego profilu i trendu masy na podstawie faktów już dostępnych w canonical workflow. Reguły rekomendacji wymagają dłuższej historii, polityk oraz celów użytkownika, dlatego nie należą do MVP Stage 8.

### Decision

- `BodyCompositionInputBuilder` normalizuje in-memory `HealthDaily.weight` bez I/O i użycia zegara;
- `BodyCompositionEngine` jest właścicielem walidacji, freshness, profilu oraz trendu;
- workflow uruchamia Body Composition po Decision i przed Nutrition;
- ten sam `BodyCompositionAssessment` jest częścią `IntelligenceDecisionResult` i `MorningCoachResult`, ale nie trafia do `RecommendationContext` ani Explainability;
- MorningCoach przekazuje istniejącą historię health i zachowuje referencję assessmentu bez interpretacji, kopiowania ani osobnej prezentacji.

### Consequences

- istnieje jeden canonical pipeline i jeden odczyt historii health;
- Body Composition pozostaje niezależne od Recommendation, Explainability, MorningCoach i infrastruktury;
- `MorningCoachReport` pozostaje kompatybilny i nie zawiera sekcji Body Composition;
- integracja Adaptive Goal Recommendation i odpowiadające explainability są regulowane osobno przez ADR-009 i pozostają poza zakresem decyzji Stage 8;

### Alternatives considered

- **Body Composition Recommendation Rule w Stage 8** — odroczona; brak wymaganej historii, polityk i celów użytkownika.
- **Uruchamianie silnika w MorningCoachUseCase** — odrzucone; use case przekazuje dane do canonical workflow.
- **Osobny workflow Body Composition** — odrzucony; tworzyłby równoległy pipeline.

## ADR-009 — Adaptive Goals

### Status

**Accepted**

### Context

Ocena celu masy ciała wymaga jawnego celu, gotowego Body Composition Assessment, osobnej oceny jakości trendu oraz istniejącego sygnału bezpieczeństwa adaptacji. Reguła Recommendation nie może odtwarzać tych danych ani interpretować surowego trendu.

### Decision

- `AthleteGoal` jest immutable konfiguracją i encją domenową poza Athlete Memory; `BodyMassTrendQuality` oraz efemeryczny `GoalAssessment` są immutable projekcjami domenowymi;
- `AthleteGoalReader` jest portem źródła aktywnego celu, a konfiguracja MVP używa bezstanowego `InMemoryAthleteGoalReader` bez I/O;
- `IntelligenceDecisionWorkflow` używa tych samych `BodyCompositionInput` i `BodyCompositionAssessment` do jednorazowej oceny trend quality;
- `GoalAssessmentEngine` otrzymuje aktywny cel, gotowe assessmenty i tę samą `AdaptationDirective`; nie tworzy rekomendacji;
- dokładnie ten sam `GoalAssessment` trafia do `RecommendationContext`, `IntelligenceDecisionResult` i `MorningCoachResult`;
- jedyny globalny Recommendation Engine uruchamia `AdaptiveGoalRecommendationRule`, która może wygenerować wyłącznie neutralne `REVIEW_BODY_COMPOSITION_TREND`;
- `GoalAssessment` nie zmienia `DecisionResult` ani decyzji treningowej;
- Presenter i `MorningCoachReport` nie analizują celu ani assessmentu i nie otrzymują nowej sekcji tekstowej;
- trwałe persistence celu wymaga przyszłego adaptera Infrastructure i nie należy do konfiguracji in-memory MVP;
- Energy Balance nie może powstać bez rzeczywistego Nutrition Intake; oba elementy pozostają poza Stage 9.

### Consequences

- cel nie zmienia decyzji treningowej ani Body Composition Assessment;
- brak celu, niepełna jakość trendu lub aktywny safety gate prowadzą do kontrolowanego braku adaptive recommendation;
- canonical workflow zachowuje jeden Recommendation Engine i jedno Explainability;
- Athlete Memory nie przechowuje konfiguracji `AthleteGoal`.

### Alternatives considered

- **Osobny Adaptive Recommendation Engine** — odrzucony jako konkurencyjny pipeline.
- **Analiza trendu w RecommendationRule** — odrzucona; reguła konsumuje wyłącznie gotowy `GoalAssessment`.
- **Reader lub GoalAssessmentEngine w MorningCoachUseCase** — odrzucone; orkiestracja należy do Intelligence Workflow.
- **DuckDB goal repository w MVP** — odroczone do osobnej decyzji persistence.

## ADR-010 — Kanoniczny Athlete Dashboard Read Model

### Status

**Accepted**

### Context

Warstwa prezentacji potrzebuje jednego, typowanego kontraktu odczytowego obejmującego gotowe wyniki kanonicznego przebiegu. Składanie takiego widoku nie może uruchamiać ponownie silników, wykonywać dodatkowych odczytów ani przenosić polityki prezentacyjnej do modeli domenowych i workflow Intelligence.

### Decision

- `dashboard/` definiuje immutable, wersjonowany i datowany `AthleteDashboard` oraz czysty, bezstanowy `DashboardEngine`;
- domeny źródłowe zachowują własność swoich danych; Dashboard jest wyłącznie efemeryczną, nieutrwalaną projekcją odczytową;
- `MorningCoachUseCase` uruchamia `DashboardEngine` dokładnie raz, po Plannerze i Presenterze, przekazując te same obiekty kanoniczne uzyskane w bieżącym przebiegu;
- `DashboardEngine` wyłącznie składa typed read model; nie podejmuje decyzji, nie generuje rekomendacji, nie interpretuje explainability i nie wykonuje I/O;
- `MorningCoachResult` transportuje Dashboard, natomiast `MorningCoachPresenter` i kompatybilny `MorningCoachReport` pozostają bez zmian funkcjonalnych;
- `DashboardEngine` jest tworzony jawnie przez composition root jako świeża zależność;
- `DashboardSerializer` jawnie mapuje pełny kontrakt v1.0 do prymitywnego payloadu oraz odtwarza go bez refleksyjnego deserializera;
- schema v1.0 jest strict: brakujące, dodatkowe lub błędnie typowane pola, nieznane enumy i nieobsługiwana wersja są odrzucane kontrolowanym błędem;
- `MorningCoachResult` transportuje model `AthleteDashboard`, a serializacja pozostaje jawnym wyborem downstream;
- persistence, transport HTTP/API, układ UI i renderowanie pozostają poza bieżącą decyzją.

### Consequences

- istnieje jeden kanoniczny kontrakt backend–presentation bez równoległego workflow;
- orkiestracja zachowuje identity gotowych wejść przekazywanych do assemblera, a wynik zachowuje ich deterministyczną kolejność;
- brak danych i pusty wynik są rozróżniane przez jawne statusy sekcji;
- integracja jest testowalna bez infrastruktury, zegara systemowego i efektów ubocznych;
- snapshoty payloadu oraz round-trip tests chronią stabilność kontraktu v1.0 bez zależności od frameworka JSON lub HTTP.
- temporal semantics, freshness i presentation ownership na granicy klientów są regulowane przez zaakceptowaną [AthleteDashboard Temporal and Presentation Contract Policy](../product/athlete-dashboard-temporal-and-presentation-policy.md); polityka nie rozszerza strict shape v1.0.

### Alternatives considered

- **Budowa Dashboardu w Presenterze** — odrzucona; zmieniałaby kompatybilny kontrakt raportu i mieszała typed read model z renderowaniem.
- **Osobny Dashboard Workflow** — odrzucony jako równoległa orkiestracja i ryzyko ponownych wywołań silników.
- **Dashboard persistence w bieżącym etapie** — odroczone; projekcja jest deterministycznie odbudowywalna z wyników bieżącego przebiegu.

## ADR-011 — Web Product Layer & Transport Boundary Architecture

### Status

**Accepted** (Dla granicy transportowej Stage 11. Production HTTP runtime pozostaje Future Decision).

### Context

Warstwa prezentacyjna Web (`AthleteWeb`) wymaga niezależnego od frameworka i środowiska mechanizmu pobierania czytelnego kontraktu odczytowego `AthleteDashboardPayloadV1`. Prezentacja nie może zależeć od bezpośrednich klas Pythona, silników domenowych ani konkretnego serwera API, a jednocześnie musi wspierać lokalne testowanie, statyczne pliki podglądu oraz zapytania HTTP.

### Decision

- `AthleteDashboard` (serializowany przez `DashboardSerializer` do ścisłego kontraktu `payload v1.0`) jest jedynym publicznym modelem odczytowym backendu dla prezentacji;
- po stronie frontendu interfejs `DashboardPayloadSource` (`load(): Promise<unknown>`) stanowi wzorzec portu warstwy prezentacji, uniezależniając UI od sposobu pobierania danych;
- `StaticJsonDashboardPayloadSource` (tryb `?source=live-file`) oraz `HttpDashboardPayloadSource` (tryb `?source=http`) reprezentują wymienne adaptery portu;
- dla rozwoju lokalnego i weryfikacji przeglądarkowej stworzono lekki, zero-dependency WSGI serwer w Pythonie (`server/app.py`) serwujący `GET /api/v1/dashboard`;
- lokalne środowisko Vite wykorzystuje same-origin proxy (`/api` → `http://127.0.0.1:8000`), eliminując problemy z polityką CORS w przeglądarce;
- interfejs użytkownika zależy wyłącznie od sześciu stanów prezentacyjnych (`ready`, `partial`, `unavailable`, `stale`, `loading`, `failure`) budowanych przez runtime parser oraz mappery prezentacyjne;
- w przypadku błędu transportu lub walidacji UI wchodzi w stan `failure` bez fallbacku do Preview Data lub statycznych plików;
- wybór produkcyjnego frameworka HTTP (FastAPI/ASGI/Uvicorn), autoryzacja, cache oraz wdrożenie chmurowe pozostają świadomie **odroczone (Future Decision)**.

### Consequences

- komponenty UI są w 100% odseparowane od backendowych klas i frameworków HTTP;
- brak wycieków danych podglądu do trybów `live-file` i `http`;
- ochrona prywatności danych zdrowotnych jest zachowana na poziomie repozytorium (pliki `.duckdb`, eksportowane pliki JSON payloadu oraz zrzuty ekranu z żywymi danymi są wykluczone z wersji Git);
- system jest testowalny jednostkowo bez działania prawdziwej sieci lub serwera API.

### Alternatives considered

- **Wbudowanie FastAPI/Uvicorn w Stage 11** — odrzucone; brak potrzeby produkcyjnego runtime na etapie budowy i walidacji warstwy UX.
- **Szeroka polityka CORS na backendzie** — odrzucona; same-origin dev proxy Vite zapewnia czystsze i bezpieczniejsze środowisko deweloperskie.

## Rejestr ADR

| ADR | Tytuł | Status | Główne źródło |
|---|---|---|---|
| ADR-001 | Modularny monolit i jawne granice | Accepted | [Architecture Baseline](../architecture.md) |
| ADR-002 | Ukończenie treningu i Athlete Memory | Accepted | [ADR-002](../adr/002-workout-completion-architecture.md) |
| ADR-003 | Athlete Intelligence | Accepted | [ADR-003](../adr/ADR-003-athlete-intelligence.md) |
| ADR-004 | Recommendation Engine | Accepted | `recommendation/`, commit history |
| ADR-005 | Jawny composition root | Accepted | `application/composition.py` |
| ADR-006 | Kanoniczny MorningCoach | Accepted | `application/morning_coach_use_case.py` |
| ADR-007 | Kanoniczna integracja Nutrition | Accepted | `application/nutrition_input.py`, `application/intelligence_decision_workflow.py` |
| ADR-008 | Body Composition Assessment | Accepted | `body_composition/`, `application/body_composition_input.py` |
| ADR-009 | Adaptive Goals | Accepted | `adaptive/`, `application/intelligence_decision_workflow.py` |
| ADR-010 | Kanoniczny Athlete Dashboard Read Model | Accepted | `dashboard/`, `application/morning_coach_use_case.py` |
| ADR-011 | Web Product Layer & Transport Boundary Architecture | Accepted | `web/AthleteWeb/`, `server/app.py`, `docs/dashboard_http_transport_boundary.md` |

## Powiązane dokumenty

- Poprzedni: [Architektura](02-architecture.md)
- Indeks: [Engineering Handbook](README.md)
- Następny: [Standardy kodowania](04-coding-standards.md)
- [Glosariusz](08-glossary.md)
