# Expert System

## Cel

Expert System odpowiada za podejmowanie decyzji na podstawie danych.

Nie korzysta z modelu AI.

Wszystkie decyzje są oparte o jawne reguły.

Model AI otrzymuje wyłącznie wynik działania systemu oraz uzasadnienie.

---

# Moduły

## 1. Readiness

Pytanie:

Czy organizm jest gotowy na zaplanowany dzień?

Wejście:

- HealthDaily
- TrainingDaily
- BloodDonation (opcjonalnie)

Wyjście:

- Status 🟢🟡🔴
- Uzasadnienie
- Jedna rekomendacja

---

## 2. Energy Balance

Pytanie:

Czy należy zmienić strategię żywieniową?

Wejście:

- HealthDaily
- TrainingDaily

Wyjście:

- Status
- Rekomendacja

---

## 3. Long-term Progress

Pytanie:

Czy realizowany plan działa?

Okres analizy:

- 7 dni
- 30 dni
- 90 dni

Wyjście:

- Trend
- Ocena

---

## 4. Alerts

Pytanie:

Czy występują niepokojące trendy?

Alert pojawia się wyłącznie po przekroczeniu ustalonych progów.

Nigdy na podstawie pojedynczego dnia.

---

## 5. Morning Briefing

Łączy wyniki wszystkich modułów.

Kolejność sekcji:

1. Stan organizmu
2. Bilans energetyczny
3. Cel długoterminowy
4. Najważniejsza rekomendacja
5. Alerty