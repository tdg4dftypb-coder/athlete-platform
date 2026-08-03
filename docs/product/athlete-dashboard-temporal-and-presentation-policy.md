# AthleteDashboard Temporal and Presentation Contract Policy

**Status:** Accepted

**Scope:** AthleteDashboard payload v1.0, Web Experience Layer i przyszły klient SwiftUI

**Decision date:** 2026-08-03

## Kontekst

`DashboardSerializer` v1.0 serializuje daty i timestampy przez `isoformat()`. Testy kontraktu potwierdzają obsługę timestampów z offsetem oraz bez offsetu. Oznacza to, że v1.0 nie gwarantuje timezone-aware `as_of`, mimo że taki format jest potrzebny na granicy backend–client.

Payload nie zawiera również identity użytkownika, postępu realizacji celu ani porównania z poprzednim dniem. Mapper nie może uzupełniać tych braków pozornie rzeczywistymi wartościami.

Dokument łączy techniczną politykę temporalną z produktową polityką freshness i presentation ownership. Rozdzielenie ich na osobne ADR/PAS zwiększałoby ryzyko sprzecznych reguł dla tego samego potoku.

## Timestamp policy

### Decyzje Accepted

1. Kanoniczny timestamp emitowany przez backend jest ISO 8601 i musi zawierać `Z` albo jawny offset.
2. Backend nie powinien generować nowych timestampów bez offsetu.
3. Klient nigdy nie interpretuje timestampu jako lokalnej strefy urządzenia.
4. Ze względu na istniejący strict contract v1.0 parser kompatybilności nadal przyjmuje legacy naive timestamp. Mapper interpretuje go deterministycznie jako UTC. Jest to reguła migracyjna, nie format docelowy.
5. Integracja transportowa nie może zostać uznana za gotową, dopóki źródło produkcyjne nie emituje aware timestampów.
6. Aware-only runtime validation jest kandydatem do payloadu v1.1. Nie wolno jednostronnie zaostrzyć parsera v1.0, ponieważ backendowe snapshoty i deserializer uznają dziś naive timestamp za prawidłowy.

### Przykłady

| Wartość | v1.0 compatibility | Polityka docelowa |
|---|---:|---:|
| `2026-08-03T06:30:15Z` | poprawna | poprawna |
| `2026-08-03T08:30:15+02:00` | poprawna | poprawna |
| `2026-08-03T06:30:15` | legacy, interpretowane jako UTC | niedozwolona w nowej emisji |
| `2026-08-03` | błędna | błędna |
| `2026-08-03T08:30:15+25:00` | błędna | błędna |
| `tomorrow` | błędna | błędna |

### Kompatybilna korekta backendu

Backend powinien tworzyć `AthleteDashboard.as_of` i timestampy rekomendacji jako aware datetime, a serializer emitować `Z` lub offset. Deserializer v1.0 może przejściowo zachować obsługę legacy naive payloadów. Taka zmiana zaostrza emisję bez usuwania możliwości odczytu istniejących danych. Nie jest wykonywana w Sprint 5.1.

## Freshness policy

### Znaczenie pól

- `valid_for_date` określa dzień produktu, dla którego zbudowano briefing. Nie jest timestampem wygenerowania.
- `as_of` określa instant, w którym zbudowano cały dashboard.
- payload v1.0 ma jeden top-level `as_of`, dlatego freshness dotyczy całego dashboardu. Per-section freshness wymaga przyszłego kontraktu.

### Reguły Accepted

1. `MappingContext.now` jest jedynym zegarem mappera.
2. Lokalna data użytkownika jest wyliczana z `now` w jawnie przekazanym `timeZone`.
3. Freshness jest oceniane dopiero dla payloadu, z którego można zbudować briefing; prawidłowy payload bez kluczowej decyzji pozostaje `unavailable`.
4. Jeśli `valid_for_date` różni się od lokalnej daty użytkownika, istniejący briefing jest `stale` niezależnie od wieku `as_of`. Dzień produktu ma pierwszeństwo w ramach oceny freshness.
5. Jeśli data jest zgodna, wiek `as_of` jest porównywany z `staleAfterMs`.
6. Dokładnie na granicy maksymalnego wieku briefing pozostaje aktualny. Dopiero przekroczenie granicy daje `stale`.
7. Timestamp z przyszłości lub nieprawidłowa konfiguracja czasu daje `failure`, nie `stale`.
8. Offset payloadu służy do wyznaczenia absolutnego instant. Nie zastępuje strefy użytkownika używanej do oceny `valid_for_date`.

### Początkowa konfiguracja

Sześć godzin zostaje przyjęte jako startowy `MORNING_BRIEFING_MAX_AGE_MS`.

Uzasadnienie produktowe: briefing jest narzędziem porannego planowania, ale powinien pozostać użyteczny przez typowe przedpołudnie i początek dnia treningowego. Po sześciu godzinach ryzyko, że synchronizacja, trening lub stan regeneracji zmieniły kontekst, jest wystarczające, aby jawnie oznaczyć dane jako stare.

Uzasadnienie techniczne: wartość jest nazwanym elementem konfiguracji klienta, przekazywanym do mappera i testowanym na granicy. Nie jest ukryta w mapperze ani pobierana z zegara systemowego. Zmiana polityki nie wymaga zmiany algorytmu mapowania.

## Presentation data ownership

| Dane UI | Własność | Zasada |
|---|---|---|
| decyzja, nazwa treningu, duration, objective | Payload-owned | mapowanie bez obliczeń |
| powody decyzji | Payload-owned | wyłącznie istniejące enumy `decision_reasons` |
| rekomendacje i ich message | Payload-owned | bez tworzenia nowych rekomendacji |
| statusy, limitations i evidence | Payload-owned | sterują partial/unavailable, nie są ukrywane |
| goal type, target i zakres dat | Payload-owned | można formatować, nie oceniać |
| `valid_for_date`, `as_of` | Payload-owned | formatowanie i freshness według tej polityki |
| `athleteName` | Client-context-owned | jawnie wymagane przez `MappingContext` |
| locale i time zone | Client-context-owned | jawnie wymagane do formatowania i lokalnej daty |
| greeting i etykiety UI | Client-context-owned | copy produktu, nie dane sportowe |
| próg freshness | Client-context-owned | nazwana konfiguracja produktu |
| `75%` realizacji celu z klasycznego Preview | Preview-only | nie może pojawić się w `source=payload` |
| „Tydzień 3 z 12” z klasycznego Preview | Preview-only | nie może być wyliczany przez mapper v1.0 |
| przykładowe „co zmieniło się od wczoraj” | Preview-only | nie może przeciekać do payload Preview |
| przykładowa narracja AI Coach | Preview-only | payload mode używa tylko treści pochodzących z payloadu i copy klienta |
| rzeczywisty procent realizacji celu | Future-contract candidate | kandydat do v1.1; wymaga definicji domenowej |
| porównanie z poprzednim dniem | Future-contract candidate | kandydat do v1.1; wymaga jawnych danych porównawczych |
| gotowa narracja briefingowa | Future-contract candidate | tylko jeśli backend ma być jej właścicielem |
| per-section `as_of` | Future-contract candidate | potrzebne do sekcyjnej freshness |

### Zasady prezentacji braków

- `goal.metadata.completeness_score` opisuje kompletność źródeł, a nie realizację celu. Nie jest pokazywane jako postęp celu.
- W payload mode brak postępu jest jawnie prezentowany jako „Postęp niedostępny”, bez `aria-valuenow` i bez wypełnienia paska.
- Bez wejściowych danych porównawczych mapper zwraca pustą listę `changesSinceYesterday`; nie generuje wniosków.
- Preview-only wartości pozostają dostępne wyłącznie w klasycznym `?state=`.

## Konsekwencje

### Backend

- Nowa emisja powinna używać aware datetime.
- Strict shape v1.0 nie może otrzymać nowych pól.
- Postęp celu, porównanie dzienne i per-section timestamps wymagają v1.1 albo późniejszej wersji.
- Legacy naive deserialization może pozostać w okresie kompatybilności.

### Web client

- Parser v1.0 zachowuje kompatybilność, a mapper nie zgaduje lokalnej strefy urządzenia.
- `MappingContext` jest obowiązkowym źródłem identity, locale, time zone, zegara i progu.
- `source=payload` nie wykorzystuje Preview-only wartości.
- `loading` nadal należy do przyszłego transportu.

### SwiftUI client

- Powinien używać tych samych reguł dnia produktu, maksymalnego wieku i timestampów.
- Calendar, Locale i TimeZone muszą być wstrzykiwane, aby Preview i testy były deterministyczne.
- Nie może przedstawiać completeness jako goal achievement ani rekonstruować comparison bez kontraktu.

## Kompatybilność i wersjonowanie

Payload v1.0 ma strict parser i dokładny zestaw pól. Dodanie pola, usunięcie pola, zmiana nullability, zawężenie do aware-only albo dodanie nowego enumu może złamać istniejącego klienta. Takie zmiany wymagają jawnej strategii migracji i — gdy zmieniają akceptowany shape — nowej wersji kontraktu.

Kandydaci v1.1: aware-only timestamps, rzeczywisty `goal_progress`, jawne `changes_since_yesterday`, opcjonalna backend-owned briefing narrative oraz per-section freshness metadata.
