# ADR-002 — Workout Completion Architecture

## Status

Accepted

## Context

Athlete Platform ma już działający, kontrolowany workflow rejestrowania ukończonego treningu:

```text
FIT
→ ParsedActivity
→ Activity
+ explicit Workout plan
→ Workout
→ PostWorkoutRecordingService
→ PostWorkoutPipeline
→ PostWorkoutResult
→ WORKOUT_COMPLETED
→ Athlete Memory
```

`FitParser` wyodrębnia dane z pliku FIT do `ParsedActivity`, a `ActivityFactory` buduje domenową `Activity`. Import wymaga jawnie wybranego planu: importer kompiluje wskazany przepis do `Workout`, a nie odgaduje planu z wykonanej aktywności. `PostWorkoutRecordingService` uruchamia `PostWorkoutPipeline`, po czym przekazuje `PostWorkoutResult` do `AthleteMemoryWriter`. Writer serializuje wynik jako append-only `WORKOUT_COMPLETED` w `athlete_memory_events`.

Problemem nie jest brak pipeline'u. Problemem jest brak formalnego kontraktu określającego, które dane w evencie są source facts, które są historyczną interpretacją analityczną, a które są wyłącznie prezentacją. Athlete Memory przechowuje obecnie fakt pojedynczej sesji wraz z jej analizą; nie jest skumulowaną wiedzą o zawodniku. Learning Engine nie istnieje i nie należy do zakresu tego ADR.

## Problem

Obecny workflow ma następujące ograniczenia kontraktowe:

1. `source_key` oparty wyłącznie o `activity.start.isoformat()` jest bieżącym mechanizmem deduplikacji, lecz nie docelową tożsamością źródła.
2. Source facts oraz derived metrics są przechowywane razem, bez formalnego logicznego rozróżnienia.
3. Feedback i teksty prezentacyjne są serializowane obok danych technicznych.
4. Nie istnieje jawna polityka wersjonowania algorytmów analizy.
5. `Activity.records` nie są zachowywane w evencie, dlatego pełna analiza blokowa nie zawsze może zostać odtworzona.
6. Nie istnieje formalna polityka replay ani re-analysis.
7. Czas występuje w kilku modelach i jednostkach: Activity oraz WorkoutSummary używają sekund, a ExecutionResult przechowuje wykonany i planowany czas w minutach.
8. Nie istnieje kontrakt definiujący minimalny historyczny zestaw danych ukończonego treningu.

## Decision

### 1. WORKOUT_COMPLETED jest niezmiennym faktem historycznym

`WORKOUT_COMPLETED` opisuje jedną ukończoną aktywność wykonaną względem jednego jawnego planu. Nie jest:

- profilem zawodnika;
- preferencją;
- trwałym wnioskiem treningowym;
- rekomendacją;
- wynikiem Learning Engine.

### 2. Jawny Workout jest wymagany

W ramach ADR-002 system nie dopasowuje automatycznie historycznego FIT do planu. Import ukończonego treningu wymaga jawnego `Workout`.

### 3. Kontrakt eventu dzieli dane logicznie

#### Event metadata

- `event_id`;
- `occurred_at`;
- `event_type`;
- `schema_version`;
- `source_type`;
- `source_key`;
- source fingerprint, gdy zostanie wdrożony.

`occurred_at` oznacza moment zakończenia aktywności. W obecnym workflow odpowiada `activity.end`; nie oznacza czasu importu ani czasu zapisu eventu.

#### Plan facts

- jednoznaczna tożsamość planu;
- typ lub goal;
- planowany czas;
- planowany TSS;
- planowany IF;
- definicja bloków albo stabilny snapshot planu.

Obecny system nie posiada stabilnego plan ID zapisywanego w evencie. Do czasu wprowadzenia takiego identyfikatora kanonicznym dowodem historycznym pozostaje zapisany snapshot planu. Przyszły stabilny plan ID, recipe ID albo fingerprint planu może uzupełnić snapshot, ale nie może go zastąpić dla już zapisanej historii.

#### Activity facts

- start;
- end;
- sport;
- czas;
- dystans;
- kalorie;
- podstawowe fakty sesji.

#### Derived analysis

- `WorkoutSummary`;
- `ExecutionResult`;
- block execution;
- `completion_score` i `execution_score`.

#### Presentation

- feedback headline;
- feedback summary;
- textual signals;
- insights.

### 4. Source facts są podstawą historii

Source facts zachowują znaczenie historyczne niezależnie od implementacji analizy. Derived analysis jest historyczną interpretacją tych danych wykonaną przez konkretną wersję algorytmu.

### 5. Derived analysis może pozostać zapisywana

Derived analysis pozostaje w evencie dla zgodności z obecnym systemem, szybkiego read-side, historycznej obserwowalności oraz dlatego, że event nie zawiera pełnych danych potrzebnych do całkowitego odtworzenia analizy blokowej.

Derived analysis nie może być jednak traktowana jako niezmienna wiedza o zawodniku.

### 6. Derived outputs muszą docelowo mieć wersję analizy

Przyszły kontrakt ma obejmować co najmniej:

- `schema_version`;
- `analysis_version`;
- `feedback_version`, jeżeli feedback pozostanie archiwizowany.

ADR-002 nie projektuje konkretnych klas ani mechanizmu wersjonowania.

### 6a. Jednostki czasu zachowują jawne znaczenie

`Activity.duration` i `WorkoutSummary.duration` są interpretowane w sekundach. `ExecutionResult.planned_duration` oraz `ExecutionResult.executed_duration` są interpretowane w minutach. Serializer i reader muszą zachowywać jawne znaczenie tych jednostek. Przyszłe ujednolicenie jednostek wymaga nowej wersji kontraktu albo jawnej migracji interpretacji.

### 7. Teksty prezentacyjne nie są źródłem prawdy

Teksty feedbacku i insights mogą pozostać dla kompatybilności, audytu oraz historycznego UI. Learning Engine nie może opierać się wyłącznie na tych tekstach.

### 8. Pełne Activity.records nie trafiają bezpośrednio do WORKOUT_COMPLETED

Athlete Memory nie jest magazynem telemetrii, a event payload nie powinien zawierać pełnego szeregu czasowego. Konsekwencją jest brak gwarancji pełnego replay analizy blokowej bez zachowanego pliku FIT albo osobnego Activity Store.

### 9. Idempotencja docelowo używa stabilnej tożsamości źródła

`activity.start.isoformat()` może pozostać mechanizmem kompatybilności, lecz nie stanowi kontraktu docelowego. Preferowany kierunek to content fingerprint lub hash źródła, zachowanie source type i stabilny source identifier. ADR-002 nie projektuje algorytmu hashowania.

### 10. Learning jest osobnym etapem

Przyszły przepływ będzie wyglądał następująco:

```text
WORKOUT_COMPLETED history
→ Learning Engine
→ Athlete Knowledge
```

ADR-002 nie dodaje eventów wiedzy.

### 11. Reader i snapshot są projekcjami

`AthleteMemoryReader` oraz `AthleteMemorySnapshot` nie są źródłem prawdy. Są ewoluującymi projekcjami historycznych eventów i mogą zmieniać się bez zmiany istniejących eventów.

## Consequences

### Positive

- Zachowana zostaje niezmienna historia ukończonych treningów.
- Powstaje podstawa dla przyszłego Learning Engine.
- Rozróżnienie facts, analysis i presentation staje się jawne.
- Algorytmy mogą ewoluować bez zmiany znaczenia source facts.
- Dalszy rozwój nie wymaga przebudowy tabeli DuckDB.

### Negative

- Częściowa denormalizacja payloadu pozostaje.
- Payload może nadal zawierać dane możliwe do wyliczenia ponownie.
- Pełny replay nie jest możliwy bez FIT albo osobnego Activity Store.
- Potrzebne będzie wersjonowanie analizy.
- Historyczne wyniki różnych wersji algorytmów mogą się różnić.

## Invariants

- Każdy `WORKOUT_COMPLETED` dotyczy dokładnie jednego `Workout` i jednej `Activity`.
- `Workout` jest jawnie wskazany.
- Event jest append-only.
- Source identity podlega idempotencji.
- Source facts nie są nadpisywane przez Learning Engine.
- Feedback nie jest trwałą wiedzą.
- Snapshot nie jest źródłem prawdy.
- Learning Engine nie zmienia historycznych eventów.
- Import nie odgaduje planu.
- Event schema jest wersjonowany.
- Historyczny `WORKOUT_COMPLETED` nie może być aktualizowany ani nadpisywany.
- Błędny event pozostaje częścią historii; mechanizm korekt albo eventów kompensacyjnych jest osobnym follow-upem i nie jest projektowany przez ADR-002.

## Migration strategy

Podejście jest przyrostowe.

### Stage 1

- Zachowanie działającego workflow.
- Formalizacja kontraktu.
- Brak migracji istniejących eventów.

### Stage 2

- Stabilna tożsamość źródła.
- Wersjonowanie analizy.
- Testy kontraktowe serializera i readera.
- Przed zapisaniem pierwszego eventu z nowym `schema_version` read-side musi obsługiwać tę wersję.
- Istniejące eventy v1 pozostają bez migracji.
- Brak obsługi nowej wersji w readerze blokuje jej zapis produkcyjny.

### Stage 3 — outside ADR-002

- Activity Store albo polityka archiwizacji FIT.
- Replay.
- Learning Engine.
- Athlete Knowledge Store.

## Scope

### Must have

- Formalny kontrakt `WORKOUT_COMPLETED`.
- Jawny `Workout`.
- Niezmienność eventu.
- Idempotencja.
- Logiczny podział danych.
- Schema version.
- Read-side dla `WORKOUT_COMPLETED`.
- Oddzielenie historii od learningu.

### Should have

- Source fingerprint.
- Analysis version.
- Polityka archiwizacji presentation.
- Kontrakt replay.
- Uporządkowanie jednostek.

### Out of scope

- Automatyczne dopasowanie planu.
- Import aktywności bez planu.
- Backfill całej historii.
- Learning Engine.
- Preferencje zawodnika.
- Threshold tolerance.
- Fatigue response.
- Adaptive planning.
- LLM.
- Zmiana algorytmu Execution Engine.
- Zmiana algorytmu Feedback Engine.
- Przebudowa tabeli event store.
- Magazynowanie pełnej telemetrii w evencie.

## Alternatives considered

### 1. Zapisywanie wyłącznie derived results

Odrzucone, ponieważ utrata source facts blokuje późniejszą reinterpretację historii.

### 2. Zapisywanie pełnej telemetrii w Athlete Memory

Odrzucone, ponieważ memory event nie powinien pełnić funkcji Activity Store.

### 3. Zapisywanie od razu trwałych preferencji i tolerancji

Odrzucone, ponieważ pojedynczy trening nie tworzy trwałej wiedzy.

### 4. Jeden duży ADR obejmujący completion, learning i adaptation

Odrzucone, ponieważ mieszałby odpowiedzialności historii wykonania, learningu i adaptacji.

## Follow-up ADR

### ADR-003 — Athlete Learning Engine

ADR-003 będzie obejmować:

- agregację wielu `WORKOUT_COMPLETED`;
- wzorce realizacji;
- adherence;
- tolerancję typów wysiłku;
- preferowaną kadencję;
- reakcję na obciążenie i regenerację;
- tworzenie Athlete Knowledge;
- wpływ wiedzy na przyszłe decyzje.
