# Architecture

## Cel

Athlete Platform jest platformą do zbierania, normalizacji i analizy danych treningowych oraz zdrowotnych.

System składa się z czterech warstw:

1. Collectors
2. Database
3. Expert System
4. AI Coach

---

## Przepływ danych

```
Apple Health
        │
Intervals.icu
        │
Body Composition
        │
Blood Tests
        │
Blood Donations
        ▼
──────────────────────
Collectors
        ▼
Data Normalization
        ▼
SQLite Database
        ▼
Expert System
        ▼
Morning Briefing
        ▼
AI Coach
```

---

## Collectors

Każdy kolektor odpowiada wyłącznie za pobranie danych z jednego źródła.

Nie wykonuje analizy.

Każdy zwraca dane zgodne z modelem z `data_model.md`.

---

## Database

Jedno centralne miejsce przechowywania danych.

Źródła danych nie komunikują się między sobą.

Komunikują się wyłącznie z bazą.

---

## Expert System

System reguł decyzyjnych.

To tutaj powstają oceny:

- Gotowość organizmu
- Bilans energetyczny
- Trendy
- Alerty

Nie korzysta z modelu AI.

---

## AI Coach

Model językowy nie podejmuje decyzji.

Otrzymuje:

- wyniki analiz,
- historię,
- kontekst.

Jego zadaniem jest:

- wyjaśnienie decyzji,
- przygotowanie porannego briefingu,
- połączenie informacji w jedną rekomendację.