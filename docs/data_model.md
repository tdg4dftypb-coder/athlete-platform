# Data Model

## Cel

Ten dokument definiuje wspólny model danych dla całej platformy.

Każdy kolektor (Apple Health, Intervals.icu itd.) odpowiada za pobranie danych
i przekształcenie ich do poniższego formatu.

Dzięki temu moduły analityczne nie muszą wiedzieć,
z jakiego źródła pochodzą dane.

---

# HealthDaily

Jedna obserwacja = jeden dzień.

| Pole | Typ | Jednostka | Opis |
|------|------|-----------|------|
| date | date | - | Data |
| weight | float | kg | Masa ciała |
| sleep_duration | int | min | Łączny czas snu |
| sleep_score | int | 1–100 | Jeżeli dostępny |
| hrv | int | ms | Średnie HRV |
| resting_hr | int | bpm | Tętno spoczynkowe |
| active_energy | int | kcal | Aktywna energia |
| resting_energy | int | kcal | Energia spoczynkowa |
| steps | int | kroki | Kroki |
| respiratory_rate | float | oddechy/min | Opcjonalnie |
| spo2 | float | % | Opcjonalnie |
| wrist_temperature | float | °C | Opcjonalnie |

---

# TrainingDaily

Jedna aktywność treningowa.

| Pole | Typ | Jednostka |
|------|------|-----------|
| date | date | |
| sport | string | |
| duration | int | min |
| distance | float | km |
| elevation | int | m |
| load | float | |
| TSS | float | |
| IF | float | |
| NP | int | W |
| FTP | int | W |
| kcal | int | |
| kJ | int | |
| avg_hr | int | bpm |
| max_hr | int | bpm |

---

# BodyComposition

Jedna analiza składu ciała.

| Pole | Typ | Jednostka |
|------|------|-----------|
| date | date | |
| weight | float | kg |
| body_fat | float | % |
| muscle_mass | float | kg |
| visceral_fat | float | |
| body_water | float | % |
| BMR | int | kcal |
| waist | float | cm |

---

# BloodTest

Jedno badanie.

| Pole | Typ | Jednostka |
|------|------|-----------|
| date | date | |
| ferritin | float | ng/ml |
| iron | float | µg/dl |
| vitamin_b12 | float | pg/ml |
| vitamin_d | float | ng/ml |
| hemoglobin | float | g/dl |
| hematocrit | float | % |
| glucose | float | mg/dl |
| hba1c | float | % |
| creatinine | float | mg/dl |
| ALT | float | U/l |
| AST | float | U/l |
| TSH | float | µIU/ml |

---

# BloodDonation

Jedno oddanie krwi.

| Pole | Typ |
|------|------|
| date | date |
| type | string |
| volume | int |
| notes | string |