# Biomarkers Laboratory PDF Import Guide

Instrukcja importu cyfrowych raportów laboratoryjnych (PDF) do modułu **Biomarkers & Laboratory Intelligence**.

---

## 1. Wymagania wstępne

- Raport laboratoryjny w formacie PDF zawierający warstwę tekstową (np. pliki PDF pobrane z portalu Pacjenta laboratoriów Synevo, Diagnostyka, ALAB).
- Aktywne środowisko wirtualne projektu (`.venv`).

> [!NOTE]
> Raporty skanowane (obrazy PDF bez warstwy tekstowej) wymagają modułu OCR, który jest celowo wyłączony w obecnym wydaniu.

---

## 2. Instrukcja Użycia CLI (`scripts/import_laboratory_pdf.py`)

### 2.1 Weryfikacja Bezpieczna (`--dry-run`)
Przed zapisaniem raportu do produkcyjnej bazy danych zaleca się wykonanie weryfikacji w trybie `--dry-run`. Podsumowanie nie zawiera surowych wartości medycznych ani danych osobowych:

```bash
.venv/bin/python scripts/import_laboratory_pdf.py /ścieżka/do/dwóch_wyników.pdf --dry-run --show-summary
```

Przykładowy wyjście CLI:
```text
[DRY-RUN] Laboratory PDF import completed successfully.
--- Execution Summary ---
  Page Count:             1
  Extracted Rows:         4
  Imported Observations:  4
  Unresolved Items:       1
  Possible Duplicates:    0
```

### 2.2 Trwały Import do Bazy DuckDB
Po potwierdzeniu w trybie dry-run wykonaj trwały import:

```bash
.venv/bin/python scripts/import_laboratory_pdf.py /ścieżka/do/dwóch_wyników.pdf --show-summary
```

Domyślnie baza danych zapisywana jest w bezpiecznej, lokalnej ścieżce `data/database/biomarkers.duckdb` (ignorowanej przez Git).

---

## 3. Opcje Wiersza Poleceń

| Opcja | Opis | Domyślnie |
| :--- | :--- | :--- |
| `pdf_path` | Ścieżka do pliku PDF z wynikami | *wymagane* |
| `--db-path` | Ścieżka do lokalnej bazy DuckDB | `data/database/biomarkers.duckdb` |
| `--dry-run` | Wykonuje ekstrakcję i analizę bez zapisu w bazie | `False` |
| `--show-summary` | Wyświetla szczegółowe wskaźniki podsumowania | `False` |
| `--lab-name` | Opcjonalne jawne nadpisanie nazwy laboratorium | `None` |

---

## 4. Gwarancje Prywatności i Bezpieczeństwa

1. **Brak Logowania Wartości Medycznych**: CLI nie drukuje surowych wyników badań ani nazwisk pacjenta na konsolę `stdout` / `stderr`.
2. **Ochrona Dokumentów Źródłowych**: Oryginalny tekst wyekstrahowany z PDF nie jest zapisywany w postaci jawnych plików na dysku.
3. **Pojedyncza Transakcja**: Bazy danych zachowują spójność — błąd podczas importu wycofuje całą transakcję.
4. **Blokada Reimportu Tombstone**: Dokument wcześniej usunięty z zachowaniem tombstone nie zostanie automatycznie zaimportowany ponownie.
