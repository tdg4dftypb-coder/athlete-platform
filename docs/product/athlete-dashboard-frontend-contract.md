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

Oficjalny payload v1.0 dopuszcza timestamp ISO zarówno z offsetem, jak i bez niego. Polityka docelowa wymaga aware timestampów w nowej emisji. Parser v1.0 zachowuje kompatybilność z legacy naive, które mapper interpretuje deterministycznie jako UTC; aware-only validation jest kandydatem v1.1.

## Mapping

Mapper nie oblicza recovery, treningu, celu ani rekomendacji. Formatuje daty i wartości, mapuje istniejące enumy na polskie etykiety oraz wybiera stan w kolejności:

1. niespójny stan po poprawnej walidacji → `failure`;
2. brak kluczowej decyzji treningowej lub rekomendacji → `unavailable`;
3. nieaktualna data lub timestamp → `stale`;
4. brakujące dane wspierające → `partial`;
5. kompletne i aktualne dane → `ready`.

`failure` oznacza naruszenie kontraktu albo niemożliwy stan mapowania. `unavailable` oznacza prawidłowy payload, który uczciwie informuje, że decyzji nie można pokazać. `loading` nigdy nie pochodzi z mappera, ponieważ opisuje przyszły stan transportu, a nie zawartość payloadu.

Payload v1.0 nie zawiera postępu realizacji celu ani porównania „od wczoraj”. Payload Preview pokazuje „Postęp niedostępny” i nie generuje porównania. Identity (`athleteName`) jest jawnym elementem `MappingContext`, nie wartością wymyślaną z payloadu.

## Freshness

Świeżość zależy od jawnego `MappingContext.now` i `staleAfterMs`. Data `valid_for_date` musi odpowiadać dacie kontekstu w podanej strefie, a wiek `as_of` nie może przekroczyć skonfigurowanego progu. Accepted startowa konfiguracja Morning Briefing wynosi sześć godzin i jest eksportowana jako `MORNING_BRIEFING_MAX_AGE_MS`.

Wiążące uzasadnienie, ownership matrix i zasady wersjonowania opisuje [Temporal and Presentation Contract Policy](athlete-dashboard-temporal-and-presentation-policy.md).

## Developer Preview

Tryb `?source=payload&fixture=<name>` uruchamia pełną ścieżkę parsera i mappera bez HTTP. Dostępne fixtures: `ready`, `partial`, `unavailable`, `stale`, `invalid-version`, `missing-section`, `invalid-enum`, `invalid-date`, `invalid-timestamp` i `malformed`. Nieznana nazwa bezpiecznie wybiera malformed fixture i prowadzi do `failure`.
