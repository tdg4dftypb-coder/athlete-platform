# 06. Lista kontrolna review

> Standard niezależnego review implementacji i architektury, przeznaczony w szczególności dla Antigravity.

## Spis treści

- [Sposób użycia](#sposób-użycia)
- [Domain](#domain)
- [Application](#application)
- [Infrastructure](#infrastructure)
- [Composition Root](#composition-root)
- [Dependency Injection](#dependency-injection)
- [Workflow](#workflow)
- [Recommendation](#recommendation)
- [Explainability](#explainability)
- [Planner](#planner)
- [MorningCoach](#morningcoach)
- [Public API](#public-api)
- [Determinism](#determinism)
- [Legacy](#legacy)
- [Regression](#regression)
- [End-to-End](#end-to-end)
- [Raport review](#raport-review)
- [Werdykty](#werdykty)
- [Powiązane dokumenty](#powiązane-dokumenty)

## Sposób użycia

1. Przeczytaj zakres zmiany, [architekturę](02-architecture.md) i powiązane [ADR-y](03-architecture-decisions.md).
2. Przejrzyj pełny diff oraz stan worktree; nie przypisuj zmian niezwiązanych do ocenianego zadania.
3. Oznacz każdą istotną uwagę priorytetem, plikiem i dowodem.
4. Odróżnij błąd od sugestii oraz istniejący problem od regresji wprowadzanej przez zmianę.
5. Sprawdź testy, nie tylko deklarację autora o ich wyniku.
6. Wydaj jeden z werdyktów z końca dokumentu.

Puste pole checklisty oznacza „niezweryfikowane”, a nie „poprawne”. Element nieadekwatny do zakresu oznacz jako N/A z krótkim uzasadnieniem.

## Domain

- [ ] Odpowiedzialność należy do właściwego bounded contextu.
- [ ] Reguła nie wykonuje I/O i nie zna infrastruktury.
- [ ] Model nie zawiera tekstu UI ani szczegółów storage.
- [ ] Fakty, projekcje, decyzje i prezentacja nie zostały pomieszane.
- [ ] Enum lub value object zastępuje powtarzany luźny string.
- [ ] Input nie jest mutowany.
- [ ] Wynik jest immutable tam, gdzie nie wymaga kontrolowanej mutacji.
- [ ] Błąd kontraktu jest jawny i czytelny.
- [ ] Nie dodano nieudokumentowanej reguły biznesowej.

## Application

- [ ] Use case tylko orkiestruje i nie duplikuje reguł.
- [ ] Workflow otrzymuje typowane wejścia i zwraca typowany wynik.
- [ ] Kolejność kroków odpowiada kanonicznemu pipeline'owi.
- [ ] Zależności są przekazane przez konstruktor.
- [ ] Application nie zależy bez potrzeby od konkretnego DuckDB lub pliku.
- [ ] Transakcje i efekty uboczne mają czytelną granicę.
- [ ] Nie powstał drugi sposób wykonania tej samej decyzji.

## Infrastructure

- [ ] Repository ogranicza się do storage i mapowania danych.
- [ ] Parser/collector tłumaczy dane na kontrakt domenowy lub aplikacyjny.
- [ ] Szczegóły tabel i formatu nie przeciekają do reguł.
- [ ] Zasoby są zamykane i mają jawny cykl życia.
- [ ] Testy używają bazy/pliku tymczasowego, nie danych produkcyjnych.
- [ ] Obsługa duplicate Source Identity nie maskuje innych constraint errors.
- [ ] Append-only semantics i schema version pozostają zachowane.
- [ ] Operacja po udanym zapisie nie udaje rollbacku, którego nie było.

## Composition Root

- [ ] Produkcyjna konfiguracja znajduje się w `application/composition.py`.
- [ ] Nowy komponent ma małą, jawną factory `build_*()` lub jest składany przez istniejącą.
- [ ] Factory nie wykonuje logiki biznesowej ani odczytu danych.
- [ ] Każde wywołanie zwraca świeżą instancję.
- [ ] Entry point pobiera gotowy use case z composition root.
- [ ] Nie utworzono drugiego composition root w skrypcie lub workflow.
- [ ] Konfiguracja Recommendation zawiera wyłącznie zaakceptowane reguły.

## Dependency Injection

- [ ] Wymagane zależności są widoczne w konstruktorze.
- [ ] Nie ma service locatora.
- [ ] Nie ma singletona ani globalnego registry.
- [ ] Nie ma import-time instancji usługi.
- [ ] Test może przekazać fake/spy bez patchowania globalnego stanu.
- [ ] Default dla kompatybilności nie ukrywa innego produkcyjnego pipeline'u.

## Workflow

- [ ] Każdy etap jest wywołany dokładnie wymaganą liczbę razy.
- [ ] Wszystkie etapy otrzymują właściwy context lub ten sam snapshot.
- [ ] Wynik komponentu jest przekazany bez niejawnej modyfikacji.
- [ ] Flattening/agregacja występuje wyłącznie u wyznaczonego właściciela.
- [ ] Pusty input ma kontrolowany wynik.
- [ ] Błąd zależności nie jest maskowany jako poprawny wynik.
- [ ] Powtórne wywołanie nie używa stanu z poprzedniego.

## Recommendation

- [ ] `DecisionEngine` pozostaje jedynym właścicielem decyzji treningowej.
- [ ] Reguła korzysta wyłącznie z `RecommendationContext`.
- [ ] Reguła zwraca tuple 0..N rekomendacji.
- [ ] Reguła nie zna innych reguł, repository, Memory ani zegara.
- [ ] Engine tylko uruchamia reguły, spłaszcza kandydatów i deleguje.
- [ ] Builder nie aktywuje rekomendacji i nie analizuje contextu.
- [ ] Deduplikacja odbywa się według `Recommendation.type`.
- [ ] Priorytet, confidence, evidence, source rules i `as_of` są scalane zgodnie z kontraktem.
- [ ] ID jest stabilne i nie używa UUID ani `hash()`.
- [ ] Wynik nie zależy od kolejności kandydatów lub reguł.
- [ ] Nowy `RecommendationType` ma kompletne mapowanie explainability.

## Explainability

- [ ] Builder otrzymuje gotowe decision reasons i recommendations.
- [ ] Nie uruchamia Decision lub Recommendation Engine.
- [ ] Nie tworzy, nie deduplikuje i nie sortuje rekomendacji.
- [ ] Zachowuje kolejność `RecommendationResult`.
- [ ] Mapowania wszystkich enumów są kompletne i walidowane.
- [ ] Brak mapowania kończy się kontrolowanym błędem.
- [ ] Tekst nie jest zapisywany jako fakt domenowy.

## Planner

- [ ] Planner otrzymuje kanoniczny `DecisionResult` i `AthleteState`.
- [ ] Nie otrzymuje ani nie analizuje `RecommendationResult`.
- [ ] Nie wybiera ponownie celu treningowego.
- [ ] Recipe selection respektuje decyzję i ograniczenia contextu.
- [ ] Parser i compiler zwracają poprawne, deterministyczne bloki.
- [ ] Jednostki czasu i TSS są jawne oraz przetestowane.
- [ ] Import rozróżnia `decision.selection.SelectionEngine` i `planner.selection.SelectionEngine`.

## MorningCoach

- [ ] `MorningCoachUseCase` wywołuje Intelligence Workflow dokładnie raz.
- [ ] Nie importuje ani nie otrzymuje `DecisionEngine`.
- [ ] Nie wywołuje Recommendation Engine lub explainability buildera bezpośrednio.
- [ ] Jeden `AthleteMemorySnapshot` zasila weekly review i Intelligence.
- [ ] Planner otrzymuje decision z `IntelligenceDecisionResult`.
- [ ] Presenter otrzymuje canonical explainability.
- [ ] Presenter nie uruchamia silników i nie tworzy rekomendacji.
- [ ] `MorningCoachReport` zachowuje publiczne pola.
- [ ] Aktywny CLI korzysta z `build_morning_coach_use_case()`.
- [ ] Legacy `MorningCoachBuilder` i `ExplanationBuilder` nie wróciły na aktywną ścieżkę.

## Public API

- [ ] Zidentyfikowano wszystkie zmienione publiczne symbole.
- [ ] `__init__.py` i `__all__` są spójne.
- [ ] Import smoke działa w świeżym procesie.
- [ ] Nie powstał cykliczny import.
- [ ] Call sites zostały znalezione i sprawdzone.
- [ ] Zmiana modelu, enuma lub sygnatury jest kompatybilna albo ma plan migracji.
- [ ] Publiczny symbol legacy nie został usunięty bez autoryzacji.

## Determinism

- [ ] Dwa uruchomienia z tym samym inputem dają równy pełny wynik.
- [ ] Domena nie używa `datetime.now()`, `date.today()` ani ukrytego zegara.
- [ ] `as_of` pochodzi z datowanego inputu.
- [ ] Kolejność nie zależy od `set`, discovery lub kolejności reguł.
- [ ] Stabilne ID nie używa `hash()` procesu.
- [ ] Komponent nie zachowuje stanu pomiędzy wywołaniami.
- [ ] Kandydaci i context nie są mutowane.

## Legacy

- [ ] Zidentyfikowano, czy zmiana dotyka CURRENT, COMPATIBILITY lub legacy path.
- [ ] Nowy kod nie zależy od legacy bez jawnej decyzji.
- [ ] Migracja nie usuwa publicznego kontraktu poza zakresem.
- [ ] Kompatybilny default nie tworzy alternatywnej logiki.
- [ ] Dokumentacja nie przedstawia legacy jako kanonicznej ścieżki.
- [ ] Martwy kod jest usuwany tylko w osobnym, zatwierdzonym zakresie.

## Regression

- [ ] Każdy naprawiony błąd ma test odtwarzający warunek.
- [ ] Test zawiódłby bez poprawki.
- [ ] Poprawka nie maskuje szerszego błędu fallbackiem.
- [ ] Testy są dodane na właściwym poziomie piramidy.
- [ ] Pełny pytest został uruchomiony dla zmiany przekrojowej.
- [ ] Skipped i warnings zostały zaraportowane.
- [ ] Diff nie zawiera niezwiązanych zmian.

## End-to-End

- [ ] Kanoniczny MorningCoach działa od kontrolowanych danych do reportu.
- [ ] Neutralny dzień ma kontrolowany wynik.
- [ ] Niska regeneracja uruchamia właściwą decyzję i rekomendację.
- [ ] Dług snu jest widoczny w rekomendacji i explainability.
- [ ] Wiele reguł daje stabilną, znormalizowaną kolejność.
- [ ] Brak danych ma kontrolowane zachowanie.
- [ ] Post-workout prowadzi od Activity + explicit Workout do eventu i snapshotu.
- [ ] Test nie modyfikuje realnej bazy ani zewnętrznego konta.

## Raport review

Raport powinien zawierać:

1. zakres i commit/diff poddany review;
2. wynik uruchomionych testów i narzędzi;
3. findings uporządkowane od najwyższego ryzyka;
4. dla każdego findingu: dowód, wpływ i minimalną poprawkę;
5. niezależnie istniejące problemy oznaczone osobno;
6. elementy N/A lub nieweryfikowalne;
7. końcowy werdykt.

Brak findings nie zwalnia z podania zakresu weryfikacji.

## Werdykty

### PASS

Zmiana spełnia kontrakt, testy i granice architektoniczne. Nie ma znanych blockerów ani wymaganych poprawek.

### PASS WITH MINOR FIX

Zmiana jest architektonicznie poprawna i bezpieczna, ale przed merge wymaga małej, lokalnej poprawki, która nie zmienia projektu ani publicznego kontraktu. Raport musi wskazać tę poprawkę jednoznacznie.

### FAIL

Zmiana narusza kontrakt, wprowadza regresję, alternatywny pipeline, niekontrolowany efekt uboczny albo nie ma wystarczających dowodów poprawności. Findings blokujące muszą zostać usunięte i ponownie zweryfikowane.

## Powiązane dokumenty

- Poprzedni: [Strategia testowania](05-testing-strategy.md)
- Indeks: [Engineering Handbook](README.md)
- Następny: [Roadmapa](07-roadmap.md)
- [Standardy kodowania](04-coding-standards.md)
- [Prompt Antigravity](prompts/antigravity.md)
