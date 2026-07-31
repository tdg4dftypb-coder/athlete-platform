# 04. Standardy kodowania

> Obowiązujące zasady implementacji dla programistów i agentów AI pracujących nad Athlete Platform.

## Spis treści

- [Zakres](#zakres)
- [Podstawowy standard](#podstawowy-standard)
- [Odpowiedzialności warstw](#odpowiedzialności-warstw)
- [Dependency Injection i Composition Root](#dependency-injection-i-composition-root)
- [Czystość domeny](#czystość-domeny)
- [Modele i niezmienność](#modele-i-niezmienność)
- [Determinizm i czas](#determinizm-i-czas)
- [I/O i stan globalny](#io-i-stan-globalny)
- [Public API](#public-api)
- [Nazewnictwo](#nazewnictwo)
- [Typowanie i kontrakty](#typowanie-i-kontrakty)
- [Błędy i walidacja](#błędy-i-walidacja)
- [Testy](#testy)
- [Standard commitów](#standard-commitów)
- [Definition of Done](#definition-of-done)
- [Instrukcja dla agentów AI](#instrukcja-dla-agentów-ai)
- [Powiązane dokumenty](#powiązane-dokumenty)

## Zakres

Standard dotyczy kodu produkcyjnego, testów, skryptów i zmian architektonicznych. W razie konfliktu pierwszeństwo mają zaakceptowane [ADR-y](03-architecture-decisions.md), następnie [referencja architektoniczna](02-architecture.md), a na końcu ten dokument.

Istniejący kod legacy może nie spełniać wszystkich reguł. Nowa zmiana nie może pogarszać granic ani kopiować odstępstwa bez jawnego uzasadnienia.

## Podstawowy standard

- Python zgodny z wersją zadeklarowaną w `pyproject.toml` (`>=3.9`).
- Kod powinien być prosty, jawny i typowany na granicach komponentów.
- Jedna klasa lub funkcja powinna mieć jedną odpowiedzialność biznesową.
- Preferuj kompozycję zamiast dziedziczenia.
- Nie dodawaj abstrakcji bez co najmniej jednego realnego kontraktu lub potrzeby testowej.
- Nie pozostawiaj `TODO`, komentarzy „future” ani martwych gałęzi w implementacji zakończonego zadania. Wyjątek stanowią jawne TODO w dokumentacji wymagane z powodu braku decyzji.
- Zachowuj publiczne kontrakty, chyba że zadanie i decyzja migracyjna wyraźnie pozwalają je zmienić.

## Odpowiedzialności warstw

### Domain

Może zawierać modele, value objects, reguły, policies i czyste obliczenia. Nie może znać DuckDB, repozytoriów, CLI, presenterów ani composition root.

### Application

Koordynuje use case i workflow. Przekazuje gotowe, typowane dane między domeną a portami. Nie duplikuje reguł i nie formatuje transportu zewnętrznego.

### Infrastructure

Implementuje storage, odczyt plików, collectory, zewnętrzne integracje i adaptery. Tłumaczy dane zewnętrzne na kontrakty używane przez aplikację.

### Presentation

Mapuje gotowe wyniki na raport, CLI, briefing lub format eksportu. Nie podejmuje decyzji i nie uruchamia reguł domenowych.

Szczegółowy podział znajduje się w [Layered Architecture](02-architecture.md#layered-architecture).

## Dependency Injection i Composition Root

- Zależności usług przekazuj przez konstruktor.
- Produkcyjne konkrety składaj w `application/composition.py` za pomocą małych `build_*()`.
- Use case otrzymuje gotowe workflow i usługi; nie tworzy ich w `run()`.
- Workflow nie tworzy repozytorium ani silnika, który orkiestruje.
- Test powinien móc przekazać fake lub spy bez patchowania globalnego kontenera.
- Każde wywołanie factory powinno zwracać świeży graf, o ile kontrakt wyraźnie nie stanowi inaczej.

Zabronione:

- framework DI bez osobnego ADR;
- service locator;
- singleton usługi;
- globalny registry;
- import-time instancja wykonująca I/O;
- ukryte tworzenie produkcyjnej zależności w metodzie biznesowej.

## Czystość domeny

Kod domenowy:

- operuje na typach domenowych, nie na wierszach bazy i surowych dictach infrastruktury;
- nie czyta ani nie zapisuje repository;
- nie renderuje tekstów użytkownika;
- nie loguje jako substytutu wyniku domenowego;
- nie zna ścieżek plików, zmiennych środowiskowych ani klientów zewnętrznych;
- zwraca wynik zamiast modyfikować dane wejściowe;
- zachowuje rozdział faktu, projekcji, decyzji i prezentacji.

Reguły Recommendation mogą korzystać wyłącznie z `RecommendationContext`. Decision Engine nie może czytać Athlete Memory bezpośrednio. Planner nie może podejmować na nowo decyzji treningowej.

## Modele i niezmienność

- Nowe value objects i wyniki przepływu definiuj jako `@dataclass(frozen=True)`, jeżeli nie wymagają kontrolowanej mutacji.
- Kolekcje w immutable modelach reprezentuj jako `tuple`, nie jako `list`.
- Nie zwracaj wewnętrznego, mutowalnego stanu komponentu.
- Nie mutuj danych wejściowych przekazanych do buildera, reguły lub workflow.
- Enumy stosuj dla zamkniętych kategorii domenowych zamiast luźnych stringów.
- Referencje do wartości enumów zapisuj jako `EnumMember` lub `.value` zgodnie z kontraktem; nie duplikuj ręcznie literałów.

Nie wszystkie historyczne modele są immutable, np. `WorkoutPlan` i `DecisionResult`. Ich zmiana wymaga osobnej migracji; nowy kod ma unikać dodatkowej mutacji tych obiektów.

## Determinizm i czas

Dla tych samych wejść komponent domenowy powinien zwracać ten sam wynik.

- Nie używaj `datetime.now()`, `datetime.utcnow()` ani `date.today()` w domenie.
- Czas przekazuj jako część inputu, `as_of`, `observed_at` lub przez jawny port zegara na granicy aplikacji.
- Fallback czasu musi pochodzić z datowanego wejścia albo zakończyć się czytelnym błędem kontraktu.
- Nie używaj w trwałej lub odtwarzalnej tożsamości wbudowanego `hash()`, którego wynik zależy od procesu.
- Dla stabilnej tożsamości używaj jawnego kontraktu, np. SHA-256.
- Nie polegaj na kolejności `set`, kolejności discovery modułów lub kolejności uruchamiania reguł.
- Sortowanie musi mieć pełny, stabilny klucz i tie-breaker.
- Losowe ID jest dopuszczalne tylko tam, gdzie identyfikuje nowy, niepowtarzalny fakt, np. append-only event; nie dla wyniku, który musi być odtwarzalny.

## I/O i stan globalny

Każda operacja I/O musi być widoczna na granicy:

- repository wykonuje zapis lub odczyt;
- parser czyta lub interpretuje format zewnętrzny;
- exporter zapisuje artefakt;
- entry point zarządza cyklem życia zasobu, np. `Database`;
- application service jawnie koordynuje porty.

Nie wolno:

- wykonywać zapytania do bazy podczas importu modułu;
- otwierać pliku w modelu domenowym;
- ukrywać zapisu w metodzie o nazwie sugerującej czyste obliczenie;
- używać globalnego, mutowalnego cache bez jawnej decyzji;
- uzależniać testów jednostkowych od produkcyjnej bazy.

## Public API

- Publiczne importy pakietu utrzymuj w jego `__init__.py` i `__all__`, jeżeli pakiet stosuje ten wzorzec.
- Nowy publiczny typ powinien mieć stabilną nazwę i jednoznaczną odpowiedzialność.
- Zmiana pól dataclass, sygnatury konstruktora, wartości enuma lub typu wyniku jest zmianą kontraktu.
- Przed zmianą API wyszukaj wszystkie call sites i testy importów.
- Migrację wykonuj kompatybilnie albo w osobnym, jawnie opisanym etapie.
- Legacy API może pozostać eksportowane, ale nie może być ponownie włączane do aktywnego pipeline'u.
- Nie usuwaj symbolu publicznego tylko dlatego, że nie występuje w kanonicznym workflow.

## Nazewnictwo

| Element | Reguła | Przykład |
|---|---|---|
| Klasa | `PascalCase`, rzeczownik lub rola | `RecommendationBuilder` |
| Funkcja/metoda | `snake_case`, czasownik opisujący efekt | `build_recommendation_engine` |
| Enum member | `UPPER_SNAKE_CASE` | `EXTEND_SLEEP` |
| Moduł | `snake_case` | `intelligence_decision_workflow.py` |
| Wynik | sufiks `Result` | `RecommendationResult` |
| Kontekst wejściowy | sufiks `Context` lub `Input` | `RecommendationContext` |
| Builder | buduje model, nie uruchamia polityki | `AthleteStateBuilder` |
| Engine | wykonuje jedną spójną zdolność domenową | `DecisionEngine` |
| Workflow/UseCase | orkiestruje gotowe komponenty | `WeeklyReviewWorkflow` |
| Factory | prefiks `build_` | `build_morning_coach_use_case` |

Unikaj nowych nazw kolidujących z istniejącymi. Repozytorium ma już dwa `SelectionEngine` i kilka historycznych obszarów Planning/Planner; import musi jasno wskazywać kontekst.

## Typowanie i kontrakty

- Typuj parametry i wartości zwracane publicznych metod.
- Używaj `Protocol` dla małych portów, gdy wiele implementacji lub fake testowy jest realną potrzebą.
- Preferuj konkretne tuple i dataclasses nad `Any` oraz niestrukturalnym dict.
- `None` oznacza jawnie opcjonalną wartość; nie używaj go jako nieudokumentowanego sentinela.
- Waliduj niepoprawny input na granicy najbliższej właścicielowi kontraktu.
- Nie łap `Exception`, jeżeli można obsłużyć konkretny typ błędu.

## Błędy i walidacja

- Błąd kontraktu ma być czytelny i wskazywać naruszone wymaganie.
- Nie stosuj cichego fallbacku, który ukrywa brak mapowania lub danych wymaganych do poprawnego wyniku.
- Błąd infrastrukturalny nie powinien być przedstawiany jako decyzja domenowa.
- Tłumacz wyjątek adaptera na błąd aplikacyjny tylko wtedy, gdy semantyka jest jednoznaczna, np. konflikt Source Identity.
- Append-only write, który się powiódł, nie może zostać przedstawiony jako cofnięty tylko dlatego, że późniejsza weryfikacja read-side zawiodła.

## Testy

Każda zmiana logiki wymaga testów na najniższym poziomie, który potwierdza zachowanie:

- reguła — osobne testy pozytywne, negatywne i graniczne;
- builder — agregacja, kolejność, brak mutacji i determinizm;
- engine — orkiestracja i delegowanie;
- workflow — kolejność oraz przekazanie dokładnie tych samych obiektów;
- repository/adapter — test integracyjny kontraktu storage lub formatu;
- regresja — test odtwarzający wykryty błąd przed poprawką;
- public API — smoke import, gdy eksport ulega zmianie.

Pełne zasady zawiera [Strategia testowania](05-testing-strategy.md).

## Standard commitów

- Commit powinien być mały, spójny i możliwy do niezależnego zweryfikowania.
- Nie łącz refaktoryzacji, zmiany zachowania i niezwiązanej dokumentacji bez potrzeby.
- Przed commitem przejrzyj `git diff` oraz uruchom testy proporcjonalne do ryzyka.
- Nie commituj baz danych, cache, sekretów ani lokalnych artefaktów, chyba że zadanie jawnie tego wymaga.
- Subject powinien krótko opisywać rezultat w trybie rozkazującym, zgodnie z dotychczasową historią, np. `Add deterministic recommendation builder`.
- Jeżeli zadanie podaje dokładną nazwę commita, użyj jej bez modyfikacji.

**TODO:** Projekt nie posiada jeszcze zaakceptowanej, jednolitej konwencji prefiksów typu Conventional Commits ani limitu długości subjectu. Do czasu decyzji nie należy narzucać ich jako obowiązkowych.

## Definition of Done

Zmiana jest ukończona, gdy:

- [ ] spełnia zaakceptowany zakres i nie dodaje funkcji poza nim;
- [ ] zachowuje odpowiedzialności warstw i nie tworzy alternatywnego pipeline'u;
- [ ] nowe zależności są jawnie wstrzyknięte i złożone w composition root;
- [ ] nie zawiera ukrytego I/O, czasu systemowego ani globalnego stanu w domenie;
- [ ] publiczne kontrakty i eksporty są celowo zachowane lub jawnie zmigrowane;
- [ ] testy jednostkowe, integracyjne i regresyjne odpowiednie dla zmiany przechodzą;
- [ ] pełny `pytest` przechodzi dla zmiany przekrojowej;
- [ ] `python3 -m compileall -q` nie zgłasza błędów dla kodu projektu;
- [ ] `git diff --check` i ręczny przegląd diffu są czyste;
- [ ] dokumentacja i ADR-y są zaktualizowane, jeżeli zmieniły się granice lub kontrakty;
- [ ] nie zmodyfikowano niezwiązanych plików.

## Instrukcja dla agentów AI

Przed zmianą agent powinien:

1. przeczytać odpowiedni fragment [architektury](02-architecture.md), ADR i testów;
2. sprawdzić stan worktree i zachować zmiany użytkownika;
3. wyszukać publiczne eksporty oraz call sites;
4. nazwać założenia, których nie da się potwierdzić w kodzie;
5. zaimplementować najmniejszą spójną zmianę;
6. dodać test regresyjny przed lub razem z poprawką;
7. uruchomić weryfikację proporcjonalną do ryzyka;
8. zaraportować zmienione pliki, wyniki testów i pozostałe ryzyka.

Agent nie może przedstawiać planowanej funkcji jako istniejącej ani „naprawiać przy okazji” niezwiązanego kodu.

## Powiązane dokumenty

- Poprzedni: [Architecture Decision Records](03-architecture-decisions.md)
- Indeks: [Engineering Handbook](README.md)
- Następny: [Strategia testowania](05-testing-strategy.md)
- [Lista kontrolna review](06-review-checklist.md)
- [Architektura](02-architecture.md)
