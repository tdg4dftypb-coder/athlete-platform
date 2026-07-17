from dataclasses import dataclass

from core.context import HealthContext


@dataclass(frozen=True)
class ReadinessResult:
    status: str


class ReadinessAnalyzer:

    def analyze(
        self,
        context: HealthContext,
    ) -> ReadinessResult:

        hrv_drop = context.hrv.delta_percent or 0.0
        rhr_rise = context.resting_hr.delta_percent or 0.0
        sleep = context.today.sleep_duration or 0

        if (
            hrv_drop <= -15
            or rhr_rise >= 15
            or sleep < 360
        ):
            return ReadinessResult(
                status="🔴 ODPUŚĆ",
            )

        if (
            hrv_drop <= -5
            or rhr_rise >= 5
            or sleep < 420
        ):
            return ReadinessResult(
                status="🟡 OSTROŻNIE",
            )

        return ReadinessResult(
            status="🟢 GOTOWY",
        )