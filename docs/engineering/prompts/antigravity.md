# Prompt — Antigravity

Użyj tego szablonu do niezależnego review.

```text
Wykonaj niezależne review wskazanego diffu/commita. Przeczytaj Architecture,
powiązane ADR-y, Testing Strategy i Review Checklist.

Zakres review: <commit/diff/moduły>
Oczekiwany kontrakt: <invariants i kryteria>

Zweryfikuj kod i testy, nie polegaj wyłącznie na raporcie autora. Szukaj
regresji, naruszeń warstw, bypassów kanonicznego workflow, ukrytego I/O,
niedeterminizmu i zmian publicznego API. Findings podaj od najwyższego
ryzyka z konkretnym dowodem i minimalną poprawką. Zakończ werdyktem:
PASS, PASS WITH MINOR FIX albo FAIL.
```

## Referencje

- [Review Checklist](../06-review-checklist.md)
- [Architecture](../02-architecture.md)
- [ADRs](../03-architecture-decisions.md)
- [Testing Strategy](../05-testing-strategy.md)
- [AI Workflow](../01-ai-workflow.md)
- [Engineering Handbook](../README.md)
- Inne role: [Codex](codex.md) · [ChatGPT](chatgpt.md)
