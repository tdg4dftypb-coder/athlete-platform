# Prompt — Codex

Użyj tego szablonu do implementacji lub refaktoryzacji w repozytorium.

```text
Przeczytaj Engineering Handbook README, Architecture, właściwe ADR-y,
Coding Standards i Testing Strategy. Sprawdź dirty worktree i zachowaj
niezwiązane zmiany.

Cel: <konkretny rezultat>
Zakres: <pliki/moduły>
Poza zakresem: <czego nie zmieniać>
Kontrakty do zachowania: <public API/invariants>
Weryfikacja: <testy, compileall, smoke>

Najpierw potwierdź stan w kodzie. Nie wymyślaj funkcji ani modułów.
Zaimplementuj najmniejszą spójną zmianę, przejrzyj diff i zaraportuj:
zmienione pliki, testy, wpływ na API oraz pozostałe ryzyka. Nie twórz
commita bez jawnego polecenia.
```

## Referencje

- [AI Workflow](../01-ai-workflow.md)
- [Architecture](../02-architecture.md)
- [ADRs](../03-architecture-decisions.md)
- [Coding Standards](../04-coding-standards.md)
- [Testing Strategy](../05-testing-strategy.md)
- [Engineering Handbook](../README.md)
- Inne role: [Antigravity](antigravity.md) · [ChatGPT](chatgpt.md)
