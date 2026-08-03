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
- `RecommendationContext` zawiera `DecisionResult`, insights, observations, opcjonalne `NutritionAssessment` i opcjonalne deterministyczne `as_of`.
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

## Rejestr ADR

| ADR | Tytuł | Status | Główne źródło |
|---|---|---|---|
| ADR-001 | Modularny monolit i jawne granice | Accepted | [Architecture Baseline](../architecture.md) |
| ADR-002 | Ukończenie treningu i Athlete Memory | Accepted | [ADR-002](../adr/002-workout-completion-architecture.md) |
| ADR-003 | Athlete Intelligence | Accepted | [ADR-003](../adr/ADR-003-athlete-intelligence.md) |
| ADR-004 | Recommendation Engine | Accepted | `recommendation/`, commit history |
| ADR-005 | Jawny composition root | Accepted | `application/composition.py` |
| ADR-006 | Kanoniczny MorningCoach | Accepted | `application/morning_coach_use_case.py` |

## Powiązane dokumenty

- Poprzedni: [Architektura](02-architecture.md)
- Indeks: [Engineering Handbook](README.md)
- Następny: [Standardy kodowania](04-coding-standards.md)
- [Glosariusz](08-glossary.md)
