# Body Composition Experience

## Cel produktu

**Body Composition Experience** odpowiada użytkownikowi na pytanie:

> **„Jak zmienia się moje ciało i czy zmiana jest zgodna z celem?”**

W myśl filozofii platformy:
- **Human Before Metrics** — najpierw wyciągnięty wniosek narracyjny, a nie surowe kilogramy;
- **Trends Before Single Measurements** — skupienie na trendzie długoterminowym, a nie pojedynczym wahań wagi porannej;
- **Transparency Builds Trust** — jawne prezentowanie braków i ograniczeń danych;
- **Progressive Disclosure** — surowe wskaźniki (np. BMI) na samym dole ekranu.

---

## Hierarchia Informacji

1. **Page Header**: Przycisk powrotu (`← Powrót`), tytuł *"Skład ciała"*, data i stan świeżości danych.
2. **Hero Body Card**: Narracja coachingowa (np. *"Masa ciała zmienia się zgodnie z planem."*), kierunek trendu, horyzont czasowy oraz badge zgodności z celem.
3. **Najważniejsze zmiany (Key Changes)**: Maksymalnie 3–4 karty podsumowujące masę ciała, obwód talii, tkankę tłuszczową i masę mięśniową.
4. **Trend masy ciała (Trend Section)**: Minimalistyczny sparkline oraz wyliczone tempo tygodniowe (np. *-0.38 kg/tydz.*).
5. **Kompozycja ciała (Breakdown)**: Zestawienie masy całkowitej, tkanki tłuszczowej, masy mięśniowej oraz obwodu talii bez dominacji BMI.
6. **Zgodność z celem (Goal Alignment)**: Wniosek czy zmiana jest zgodna z założonym celem oraz zalecane tempo.
7. **Jakość danych (Data Quality)**: Wyraźne i jawne prezentowanie braków pomiarowych, nieregularności lub braku obwodów.
8. **Regional Body Change Map (Placeholder)**: Informacyjny, nieaktywny element informujący o planowanej w przyszłości funkcji.
9. **Dane i wskaźniki techniczne (Technical Metrics)**: Tabela szczegółowych pomiarów technicznych (w tym BMI) na samym dole ekranu.

---

## Sześć Stanów Prezentacyjnych

| Stan | Zachowanie |
| :--- | :--- |
| **`ready`** | Pełen widok interpretacji, trendu, składu oraz wskaźników technicznych. |
| **`partial`** | Komunikat o częściowości danych z jawnym wykazem brakujących pomiarów. |
| **`unavailable`** | Brak wpisów wagi w ciągu ostatnich 28 dni; czysty komunikat z akcją rejestracji pomiaru. |
| **`stale`** | Widok danych z poprzedniego dnia z wyraźnym ostrzeżeniem o braku odświeżenia. |
| **`loading`** | Szkielet struktury z `aria-busy="true"` i etykietą stanu. |
| **`failure`** | Komunikat błędu pobierania z przyciskiem ponowienia akcji. |

---

## Różnice pomiędzy Preview Data a Payload Mode

- **Preview Data (`source="preview"`)**: Zawiera kompletne dane demonstracyjne, w tym obwód talii, tkankę tłuszczową oraz historyczny trend 28-dniowy.
- **Payload Mode (`source="payload"`)**: Rygorystyczne odwzorowanie schema payload v1.0. Jeśli pola `waist_circumference_cm`, `body_fat_percent` lub punkty trendu są niedostępne (`null`), kod **nie generuje fikcyjnych wartości**, lecz jawnie oznacza je jako brakujące w sekcji Jakość Danych.

---

## Ograniczenia Contract v1.0 i Przyszłe Rozszerzenia

- Payload v1.0 przechowuje zagregowane metryki masy i tkanki tłuszczowej, ale nie dostarcza regionalnego podziału tkanki (barki, brzuch, uda).
- **Future Candidate**: Regional Body Change Map została ujęta w architekturze jako nieaktywny placeholder informacyjny.

---

## Routing i Dostępność

- **URL**: `?view=body` (oraz `?view=body&state=...`).
- Dostęp z ekranów: Morning Briefing, Progress Experience, przyszłej sekcji Więcej.
- Brak modyfikacji dolnego paska nawigacji głównej.
