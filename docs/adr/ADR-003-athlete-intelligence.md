# ADR-003 — Athlete Intelligence

## Status

Accepted

## Context

Athlete Platform przechowuje historyczne zdarzenia ukończonych treningów w
Athlete Memory. Read-side buduje z nich typowany snapshot, ale snapshot ani
eventy nie są bezpośrednim wejściem dla polityki decyzyjnej. Platforma potrzebuje
małej, deterministycznej warstwy, która potrafi opisać zaobserwowane zachowania
bez zamieniania analizy historycznej w trwałą wiedzę o zawodniku.

## Decision

Athlete Intelligence ma następujący przepływ:

```text
HealthObservationInput + AthleteMemorySnapshot
↓
ObservationProjector
↓
AthleteObservation
↓
InsightBuilder
↓
AthleteInsight
↓
DecisionEngine
```

`DecisionEngine` otrzymuje gotowe, immutable insighty razem z `AthleteState`
i opcjonalną dyrektywą adaptacji. Nie otrzymuje repository ani bezpośredniego
dostępu do Athlete Memory.

### Observations

`AthleteObservation` jest efemeryczną, deterministyczną projekcją danych
dostępnych w read-side. Zawiera wartość, confidence, moment obserwacji oraz
evidence. Nie jest źródłem prawdy, eventem ani trwałym rekordem wiedzy.

### Insights

`AthleteInsight` jest efemeryczną, deterministyczną projekcją jednej lub wielu
obserwacji. Zawiera typ, confidence, evidence oraz `as_of`.

`as_of` oznacza najpóźniejszy moment objęty evidence insightu. Nie oznacza czasu
wykonania kodu, czasu zapisu ani niezależnego czasu wygenerowania. Dzięki temu
pozostaje deterministyczny dla tego samego zestawu obserwacji.

Insight nie jest źródłem prawdy, nie jest eventem Athlete Memory i nie jest
trwałą wiedzą o zawodniku.

### Domain and presentation

Modele domenowe Observation i Insight nie zawierają tekstów prezentacyjnych.
Tekst dla użytkownika jest odpowiedzialnością warstwy explainability lub
renderera, która mapuje stabilne typy na komunikaty.

### Evidence and decision boundary

Evidence jest przekazywane jako stabilne referencje do źródłowych eventów.
ObservationProjector i InsightBuilder nie zapisują danych, nie korzystają z
infrastruktury i nie podejmują decyzji treningowych. Gotowe insighty są
przekazywane do Decision Engine dokładnie w kanonicznym przebiegu workflow.

## Consequences

- Historia pozostaje w Athlete Memory, a projekcje mogą być przeliczane.
- Intelligence nie wymaga nowego repository ani nowego event contractu.
- Teksty UI nie stają się faktami domenowymi.
- Późniejsze reguły insightów mogą być dodawane przez jawny kontrakt reguły,
  bez zmiany granicy Athlete Memory.

## Out of scope

- trwały Knowledge Store;
- Knowledge Engine;
- bezpośredni dostęp Decision Engine do repository lub Athlete Memory;
- nowe typy Observation lub Insight;
- LLM jako źródło prawdy;
- zmiana eventów, Source Identity lub Athlete Memory.
