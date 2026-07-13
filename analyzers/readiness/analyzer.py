from core.context import HealthContext
from core.results import AnalyzerResult


class ReadinessAnalyzer:

    GREEN = 0
    YELLOW = 1
    RED = 2

    def analyze(self, context: HealthContext) -> AnalyzerResult:

        reasons = []

        hrv_level = self._hrv(context, reasons)
        rhr_level = self._rhr(context, reasons)
        sleep_level = self._sleep(context, reasons)

        overall = max(
            hrv_level,
            rhr_level,
            sleep_level,
        )

        if overall == self.GREEN:

            return AnalyzerResult(
                status="🟢 GOTOWY",
                explanation="Brak niepokojących sygnałów.",
                recommendation="Realizuj zaplanowany trening."
            )

        if overall == self.YELLOW:

            return AnalyzerResult(
                status="🟡 OSTROŻNIE",
                explanation=" ".join(reasons),
                recommendation="Zachowaj plan, ale unikaj dodatkowego obciążenia."
            )

        return AnalyzerResult(
            status="🔴 ODPUŚĆ",
            explanation=" ".join(reasons),
            recommendation="Priorytetem powinna być regeneracja."
        )

    # -------------------------------------------------

    def _hrv(self, context, reasons):

        change = context.hrv.delta_percent

        if change is None:
            return self.GREEN

        if change <= -15:
            reasons.append(
                f"HRV spadło o {abs(change):.1f}%."
            )
            return self.RED

        if change <= -5:
            reasons.append(
                f"HRV jest niższe o {abs(change):.1f}%."
            )
            return self.YELLOW

        return self.GREEN

    # -------------------------------------------------

    def _rhr(self, context, reasons):

        delta = context.resting_hr.delta

        if delta is None:
            return self.GREEN

        if delta >= 8:
            reasons.append(
                f"Tętno spoczynkowe wzrosło o {delta:.0f} bpm."
            )
            return self.RED

        if delta >= 4:
            reasons.append(
                f"Tętno spoczynkowe jest podwyższone o {delta:.0f} bpm."
            )
            return self.YELLOW

        return self.GREEN

    # -------------------------------------------------

    def _sleep(self, context, reasons):

        if context.today.sleep_duration is None:
            return self.GREEN

        hours = context.today.sleep_duration / 60

        if hours < 6:
            reasons.append(
                "Spałeś mniej niż 6 godzin."
            )
            return self.RED

        if hours < 7:
            reasons.append(
                "Sen był krótszy niż zalecane 7 godzin."
            )
            return self.YELLOW

        return self.GREEN