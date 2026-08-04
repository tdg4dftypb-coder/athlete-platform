# Recovery Experience

## Cel ekranu

Recovery Experience jest pierwszym pełnym ekranem szczegółowym webowego Experience Layer. Odpowiada na pytanie: **„Jak mój organizm się regeneruje i co wpłynęło na dzisiejszą ocenę?”**

Ekran nie oblicza Recovery Score, nie ustala gotowości treningowej i nie podejmuje nowej decyzji. Pokazuje gotowy wynik oraz dostępne czynniki zgodnie z zasadami Decision First, Human Before Metrics, Progressive Disclosure, Transparency Builds Trust i Calm Technology.

## Hierarchia informacji

1. **Jak wygląda regeneracja?** — hero ze statusem prezentacyjnym, narracją i Recovery Score, wyłącznie jeśli istnieje.
2. **Dlaczego?** — HRV, sen, tętno spoczynkowe oraz zmęczenie, każdy z tekstowym statusem, wartością i opisem.
3. **Co to oznacza na dziś?** — prezentacyjne objaśnienie relacji z gotową decyzją treningową, bez jej ponownego wyznaczania.
4. **Trend** — tylko dla jawnych Preview Data. Payload v1.0 nie zawiera historii ani baseline'ów potrzebnych do prawdziwego trendu.
5. **Dane szczegółowe** — ograniczona lista częstości oddechu i saturacji, jeśli są dostępne. Temperatura nadgarstka nie jest pokazywana bez indywidualnego kontekstu.

## Model prezentacyjny

`RecoveryPresentation` zawiera wyłącznie dane gotowe do renderowania:

- jawne `source`: `preview` albo `payload`;
- nagłówek, aktualizację i status świeżości;
- hero z opcjonalnym wynikiem;
- cztery czynniki regeneracji;
- interpretację na dziś;
- opcjonalne dane szczegółowe;
- opcjonalne podsumowanie trendu.

`RecoveryPresentationState` jest discriminated union z wariantami `ready`, `partial`, `unavailable`, `stale`, `loading` i `failure`. Nie istnieją luźne flagi, które mogłyby stworzyć sprzeczny stan.

## Komponenty

- `PageHeader` — tytuł, aktualizacja, świeżość i dostępny klawiaturowo powrót;
- `StatusHero` — najważniejszy wniosek i opcjonalny source Recovery Score;
- `MetricSummary` — pojedynczy czynnik z tekstowym statusem, wartością i opisem;
- `ExplanationSection` — gotowa informacja „Co to oznacza na dziś?”;
- `TrendIndicator` — używany tylko, gdy źródło naprawdę dostarcza trend;
- współdzielone `StatusNotice` — stany partial, unavailable, stale i failure;
- współdzielona dolna nawigacja — bez nowej głównej zakładki Recovery.

Komponenty są wyodrębnione tylko tam, gdzie istnieje realne współdzielenie. Recovery-specific hero i factor cards pozostają wewnątrz feature slice.

## Sześć stanów

| Stan | Zachowanie |
|---|---|
| `ready` | Najpierw pokazuje ocenę, następnie czynniki, interpretację i dostępne szczegóły. |
| `partial` | Zachowuje dostępny wynik, wymienia brakujące dane i nie generuje brakujących wartości ani trendów. |
| `unavailable` | Wyjaśnia brak oceny i nie renderuje Recovery Score ani czynników. |
| `stale` | Zachowuje dane za jawnym ostrzeżeniem z czasem ostatniej aktualizacji. |
| `loading` | Ustawia `aria-busy`, udostępnia live status i stabilny przestrzennie skeleton. |
| `failure` | Rozróżnia błąd operacyjny od braku danych i udostępnia jedną akcję retry. |

Kolor wspiera tekst, ale nie jest jedynym nośnikiem stanu. Zieleń oznacza obszar Recovery, bursztyn ograniczoną kompletność lub świeżość, koral błąd. W trybie payloadowym zieleń nie oznacza automatycznie „dobrego” wyniku.

## Preview a payload

Preview Data są deterministycznym, demonstracyjnym scenariuszem UX. Mogą pokazywać przykładowe statusy jakościowe, porównania i trend, ponieważ są jawnie oznaczone `source=preview`.

Ścieżka payloadowa ma granicę:

```text
unknown
→ runtime parser payloadu v1.0
→ Recovery mapper
→ RecoveryPresentationState
→ Recovery Experience
```

Mapper payloadu:

- nie ustala progów Recovery Score;
- nie określa „dobrej” lub „słabej” regeneracji z liczby;
- nie generuje trendów, baseline'ów ani historii;
- nie zamienia `null` na zero;
- nie pokazuje surowych kodów evidence i limitations jako tekstu UI;
- może formatować istniejące wartości i opisać ich dostępność;
- może odwołać się do istniejących decision reasons, ale nie podejmuje nowej decyzji.

## Nawigacja

Morning Briefing jest widokiem domyślnym. Recovery otwiera się przez:

- aktywny kafel „Regeneracja”;
- przycisk „Pokaż szczegóły” w sekcji „Dlaczego właśnie taki plan?”;
- `?view=recovery` dla deep linku i developerskiego Preview.

`?view=recovery&state=<kind>` wybiera jeden z sześciu stanów. `?view=recovery&source=payload&fixture=<name>` przechodzi przez parser i mapper. Nieznany widok wraca do Morning Briefing. Powrót usuwa widok szczegółowy bez dodawania Recovery do dolnej nawigacji.

## Ograniczenia payloadu v1.0

Payload v1.0 dostarcza bieżący Recovery Score, sleep score oraz wybrane metryki health/performance. Nie dostarcza:

- semantycznego statusu jakości regeneracji;
- domenowej narracji Recovery;
- statusu i wyjaśnienia pojedynczych czynników;
- baseline'ów i zmian względem poprzedniego okresu;
- historii punktów pomiarowych;
- jawnego związku każdego czynnika z Recovery Score.

Z tego powodu prezentacja payloadowa używa neutralnego określenia „Ocena regeneracji dostępna”, nawet gdy liczbowy wynik jest wysoki.

## Kandydaci payloadu v1.1

- `recovery_status` o ustalonej semantyce domenowej;
- gotowe `recovery_narrative` i `today_interpretation`;
- typed factor assessments dla HRV, snu, RHR i zmęczenia;
- baseline, delta i jawny kierunek trendu każdego czynnika;
- ograniczona historia potrzebna do mini-trendu;
- prezentacyjne, stabilne kody przyczyn zamiast interpretowania evidence;
- jawna informacja, które czynniki wpłynęły na wynik.

Zmiany te wymagają osobnej decyzji kontraktowej. Nie należą do Sprintu 6 i nie zostały dodane do backendu.
