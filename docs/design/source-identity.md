# Source Identity

## Cel

Athlete Platform potrzebuje trwałej identyfikacji jednego rekordu w konkretnym zewnętrznym providerze. Jest to potrzebne dla obecnych i przyszłych źródeł: FIT, Garmin Connect, Strava, Apple Health, Wahoo oraz kolejnych integracji.

Source Identity pozwala traktować dane jako pochodzące z określonego rekordu zewnętrznego, a nie jako anonimowy zestaw wartości odebrany w danym momencie przez Platformę.

## Problem

Obecny mechanizm:

```text
source_key = activity.start.isoformat()
```

jest mechanizmem kompatybilności. Oznacza moment rozpoczęcia aktywności, ale nie trwałą tożsamość jej źródła. Różne dane mogą zaczynać się w tym samym czasie, a te same dane mogą zostać pobrane wielokrotnie pod inną nazwą lub z innej ścieżki.

Dlatego czas rozpoczęcia jest użytecznym faktem historycznym, lecz nie docelową odpowiedzią na pytanie, skąd dokładnie pochodzą dane.

## Rozróżnienie pojęć

**Source** to zewnętrzny system albo nośnik danych, na przykład plik FIT, Garmin Connect, Strava lub Apple Health.

**Source Record** to pojedynczy rekord albo artefakt w zewnętrznym źródle.

**Source Identity** to tożsamość Source Record w obrębie konkretnego providera.

**Activity** to domenowa reprezentacja wykonanej aktywności utworzona na podstawie danych ze źródła.

**Canonical Activity Identity** to przyszła wewnętrzna tożsamość domenowej Activity. Pozostaje poza zakresem tego dokumentu.

**Workout** to jawny plan treningu, względem którego aktywność może zostać przeanalizowana. Nie jest tożsamy ze źródłem danych ani z wykonaną aktywnością.

**WORKOUT_COMPLETED** to historyczny event łączący jedną Activity z jednym jawnym Workout oraz wynikami analizy wykonania.

```text
Source
→ Source Record
→ Activity
+ Workout
→ WORKOUT_COMPLETED
```

Wiele Source Records może w przyszłości zostać powiązanych z jedną Canonical Activity. Samo takie powiązanie nie wynika jednak z Source Identity.

## Source Identity

Source Identity składa się z:

- `provider`;
- `external_id`.

`provider` identyfikuje zewnętrzny system albo typ źródła. `external_id` identyfikuje jeden Source Record w obrębie tego providera. Para `provider + external_id` stanowi Source Identity.

Nie identyfikuje:

- zawodnika;
- Workout;
- eventu `WORKOUT_COMPLETED`;
- Athlete Knowledge;
- kanonicznej domenowej Activity.

Source Identity odpowiada wyłącznie na pytanie: „czy to jest ten sam rekord w obrębie tego samego providera?”.

## Przykłady

Przykładowe wartości kontraktu mogą wyglądać następująco:

```text
provider = fit_file
external_id = <wartość ustalona przez adapter FIT>

provider = garmin_connect
external_id = <identyfikator rekordu Garmin>

provider = strava
external_id = <identyfikator aktywności Strava>

provider = apple_health
external_id = <identyfikator treningu Apple Health>
```

Są to przykłady wartości wspólnego kontraktu, a nie propozycja hierarchii klas, interfejsów ani provider-specific typów.

## Zasady architektoniczne

- Domena nie zna sposobu identyfikacji źródła.
- Adapter infrastrukturalny tworzy Source Identity.
- Warstwy downstream używają wyłącznie kontraktu Source Identity.
- Dodanie kolejnego źródła nie wymaga zmiany domeny treningowej.
- Source Identity nie rozstrzyga, czy rekordy od różnych providerów opisują ten sam fizyczny trening.

## Relacja z ADR-002

[ADR-002 — Workout Completion Architecture](../adr/002-workout-completion-architecture.md) definiuje kontrakt historycznego eventu `WORKOUT_COMPLETED`.

Source Identity jest tylko jednym z elementów metadanych takiego eventu. Ten dokument nie zmienia decyzji ADR-002; opisuje wyłącznie wspólne znaczenie Source Identity dla przyszłych źródeł danych.

## Out of scope

Dokument nie opisuje mechanizmów technicznych, sposobu wyznaczania identyfikatorów, storage, indeksowania, migracji, zachowania przy ponownym imporcie ani implementacji. Poza zakresem pozostają również multi-source deduplication, entity resolution oraz Canonical Activity Identity.

Dokument nie przyjmuje konkretnego mechanizmu identyfikacji FIT. Jego wybór wymaga osobnego audytu rzeczywistych danych FIT.
