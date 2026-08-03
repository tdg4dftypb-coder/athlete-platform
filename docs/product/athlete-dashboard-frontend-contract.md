# AthleteDashboard — frontend contract boundary

## Przepływ

```text
raw unknown payload
→ parseAthleteDashboardPayloadV1
→ AthleteDashboardPayloadV1
→ mapAthleteDashboardToMorningBriefing
→ MorningBriefingPresentationState
→ UI
```

Frontendowy typ opisuje wyłącznie publiczne prymitywy emitowane przez `DashboardSerializer` v1.0. Nie importuje modeli domenowych backendu. Wszystkie sekcje są obowiązkowe: `health`, `recovery`, `performance`, `training`, `nutrition`, `body_composition`, `goal`, `recommendations` i `data_quality`. Brak danych jest wyrażany przez `metadata.status` oraz kontraktowe `null`, nigdy przez usunięcie sekcji.

## Runtime validation

Lekki parser bez zależności zewnętrznych przyjmuje `unknown` i zwraca discriminated union `success`/`failure`. Sprawdza dokładny zestaw pól, wersję `1.0`, typy prymitywów, skończone liczby, integer fields, dozwolone `null`, listy, wszystkie publiczne enumy, kanoniczne daty oraz timestampy ISO. Nieznane pola i enumy są odrzucane.

Oficjalny payload v1.0 dopuszcza timestamp ISO zarówno z offsetem, jak i bez niego. Mapper interpretuje wariant bez offsetu deterministycznie jako UTC. Ujednolicenie kontraktu do obowiązkowego aware timestamp wymaga osobnej decyzji i nowej wersji lub doprecyzowania kontraktu; frontend nie zaostrza jednostronnie v1.0.

## Mapping

Mapper nie oblicza recovery, treningu, celu ani rekomendacji. Formatuje daty i wartości, mapuje istniejące enumy na polskie etykiety oraz wybiera stan w kolejności:

1. niespójny stan po poprawnej walidacji → `failure`;
2. brak kluczowej decyzji treningowej lub rekomendacji → `unavailable`;
3. nieaktualna data lub timestamp → `stale`;
4. brakujące dane wspierające → `partial`;
5. kompletne i aktualne dane → `ready`.

`failure` oznacza naruszenie kontraktu albo niemożliwy stan mapowania. `unavailable` oznacza prawidłowy payload, który uczciwie informuje, że decyzji nie można pokazać. `loading` nigdy nie pochodzi z mappera, ponieważ opisuje przyszły stan transportu, a nie zawartość payloadu.

Payload v1.0 nie zawiera postępu realizacji celu ani porównania „od wczoraj”. UI pokazuje więc `goal.metadata.completeness_score` wyłącznie jako jawnie podpisaną kompletność danych celu i nie generuje porównania. Identity (`athleteName`) jest jawnym elementem `MappingContext`, nie wartością wymyślaną z payloadu.

## Freshness

Świeżość zależy od jawnego `MappingContext.now` i `staleAfterMs`. Data `valid_for_date` musi odpowiadać dacie kontekstu w podanej strefie, a wiek `as_of` nie może przekroczyć skonfigurowanego progu. Próg sześciu godzin występuje wyłącznie w deterministycznym Preview Sprintu 5. Nie jest zatwierdzoną polityką produktu i wymaga późniejszego ADR/PAS przed integracją transportową.

## Developer Preview

Tryb `?source=payload&fixture=<name>` uruchamia pełną ścieżkę parsera i mappera bez HTTP. Dostępne fixtures: `ready`, `partial`, `unavailable`, `stale`, `invalid-version`, `missing-section`, `invalid-enum`, `invalid-date`, `invalid-timestamp` i `malformed`. Nieznana nazwa bezpiecznie wybiera malformed fixture i prowadzi do `failure`.
