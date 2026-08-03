# Morning Briefing — Visual Reference v1

## Status

Kanonicznym źródłem prawdy dla wyglądu stanu `ready` jest
[`references/morning-briefing-reference-v1.png`](references/morning-briefing-reference-v1.png).
Referencja określa kierunek Experience Layer, a nie kontrakt danych ani zachowanie domenowe.

## Elementy obowiązkowe

- poziomy nagłówek z neutralnym awatarem, powitaniem, datą i dyskretnym oznaczeniem AI Coach;
- jasny, przestrzenny hero z pastelowym gradientem, wyraźną hierarchią narracji i demonstracyjnym przyciskiem audio;
- jedna spójna powierzchnia decyzji obejmująca decyzję, powody, dostępne porównanie oraz plan dnia;
- semantyczne, spójne ikony SVG i stałe znaczenie kolorów Recovery, Training, Sleep oraz Attention;
- karta celu z szerokim paskiem postępu oraz cztery lekkie kafle „Dowiedz się więcej”;
- ikonowa dolna nawigacja respektująca sticky positioning, focus i safe area.

Typografia, promienie, rytm odstępów, lekkie cienie oraz proporcja treści do pustej przestrzeni powinny pozostać możliwie bliskie referencji. Fotografia i status bar widoczne w makiecie nie są częścią implementacji webowej.

## Adaptacja responsywna

Na szerokościach 390–430 px powody decyzji i zmiany pozostają w trzech kolumnach. Poniżej 368 px powody mogą przejść do jednej kolumny, a nagłówek może przenieść oznaczenie coacha do drugiego wiersza. Kafelki „Dowiedz się więcej” używają dwóch kolumn w webowym shellu, aby zachować czytelność tekstu i minimalne cele dotykowe; makieta może pokazywać cztery bardziej zwarte kafle w jednym rzędzie.

Na desktopie shell pozostaje wyśrodkowany i zachowuje mobilną szerokość. Powiększenie tekstu może zwiększyć wysokość elementów, ale nie może obcinać treści ani powodować poziomego przewijania.

## Preview Data a payload source

Klasyczne Preview może pokazywać demonstracyjne `75%`, „Tydzień 3 z 12” oraz porównanie z wczoraj. Tryb `source=payload` nie uzupełnia tych danych: brak rzeczywistego postępu pozostaje oznaczony jako niedostępny, a karta porównania nie jest renderowana. `completeness_score` nie jest postępem celu.

Referencja dotyczy przede wszystkim kompletnego stanu `ready`. Stany `partial`, `unavailable`, `stale`, `loading` i `failure` współdzielą shell, nagłówek, tokeny, powierzchnie i nawigację, ale zachowują własną semantykę i komunikaty.

## Zasady przyszłych zmian

Zmiana hierarchii, układu głównych powierzchni, ikonografii lub semantyki kolorów wymaga aktualizacji tej decyzji i zatwierdzonej referencji. Drobne adaptacje dostępności i responsywności są dozwolone, jeżeli nie osłabiają hierarchii. Referencja ma pierwszeństwo przed wcześniejszą decyzją o skrótach jako liście w stylu Ustawień; powrót do czterech kafli jest świadomą korektą wynikającą z wyboru kanonicznego wzorca.
