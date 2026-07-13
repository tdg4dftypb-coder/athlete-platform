from core.context import HealthContext
from core.results import AnalyzerResult


class EnergyBalanceAnalyzer:

    GREEN = 0
    YELLOW = 1
    RED = 2

    def analyze(self, context: HealthContext) -> AnalyzerResult:

        reasons = []

        training = self._training(context, reasons)
        weight = self._weight(context, reasons)

        overall = max(training, weight)

        if overall == self.GREEN:

            return AnalyzerResult(
                status="🟢 NORMALNIE",
                explanation="Bilans energetyczny wygląda prawidłowo.",
                recommendation="Nie ma potrzeby zmiany podaży energii."
            )

        if overall == self.YELLOW:

            return AnalyzerResult(
                status="🟡 ZWIĘKSZ ENERGIĘ",
                explanation=" ".join(reasons),
                recommendation="Dzisiaj zwiększ podaż węglowodanów."
            )

        return AnalyzerResult(
            status="🔴 NISKA DOSTĘPNOŚĆ ENERGII",
            explanation=" ".join(reasons),
            recommendation="Priorytetem jest uzupełnienie energii."
        )

    # -------------------------------------------------

    def _training(self, context, reasons):

        training = context.training

        if training is None:
            return self.GREEN

        if training.tss is not None and training.tss >= 120:
            reasons.append("Zaplanowano bardzo wymagający trening.")
            return self.YELLOW

        if training.kj is not None and training.kj >= 1800:
            reasons.append("Trening będzie wymagał dużych zasobów energetycznych.")
            return self.YELLOW

        return self.GREEN

    # -------------------------------------------------

    def _weight(self, context, reasons):

        if context.body is None:
            return self.GREEN

        # Placeholder.
        # Tutaj później wykorzystamy TrendEngine
        # do oceny tempa zmian masy ciała.

        return self.GREEN