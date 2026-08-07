from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from application.morning_coach_use_case import MorningCoachResult, MorningCoachUseCase
    from biomarkers.dashboard import BiomarkersDashboardBuilder

from morning_briefing.input_models import (
    BiomarkerBriefingInput,
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
)
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


class ProductionMorningBriefingInputProvider(MorningBriefingInputProvider):
    """Production provider connecting real Athlete Platform data sources to MorningBriefingInput.

    Performs a single logical snapshot fetch per get_input() call:
    - Invokes MorningCoachUseCase.run() at most ONCE.
    - Invokes BiomarkersDashboardBuilder.build() at most ONCE.
    - Maps read models without recalculating domain scores or classifying biomarkers.
    """

    def __init__(
        self,
        morning_coach_use_case: MorningCoachUseCase | Callable[[], MorningCoachUseCase],
        biomarkers_dashboard_builder: BiomarkersDashboardBuilder | Callable[[], BiomarkersDashboardBuilder] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if morning_coach_use_case is None:
            raise TypeError("morning_coach_use_case must not be None")

        self._morning_coach_use_case = morning_coach_use_case
        self._biomarkers_dashboard_builder = biomarkers_dashboard_builder
        self._clock = clock or (lambda: datetime.now(tz=timezone.utc))

    def get_input(self) -> MorningBriefingInput:
        generated_at = self._clock()

        # 1. Single snapshot fetch from MorningCoachUseCase (tight error boundary for source call)
        coach_result: MorningCoachResult | None = None
        try:
            if callable(self._morning_coach_use_case) and not hasattr(self._morning_coach_use_case, "run"):
                use_case = self._morning_coach_use_case()
            else:
                use_case = self._morning_coach_use_case
            coach_result = use_case.run()
        except Exception as err:
            raise MorningBriefingInputError("Failed to load MorningCoach data source") from err

        if coach_result is None:
            raise MorningBriefingInputError("MorningCoachUseCase returned null result")

        # 2. Single snapshot fetch from BiomarkersDashboardBuilder (tight error boundary for source call)
        dashboard: Any = None
        if self._biomarkers_dashboard_builder is not None:
            try:
                if callable(self._biomarkers_dashboard_builder) and not hasattr(self._biomarkers_dashboard_builder, "build"):
                    builder = self._biomarkers_dashboard_builder()
                else:
                    builder = self._biomarkers_dashboard_builder

                dashboard = builder.build()
            except Exception as err:
                raise MorningBriefingInputError("Failed to load Biomarkers data source") from err

        # Pure read-side mapping logic outside source try/except blocks

        # 3. Biomarkers Mapping
        # Note on Biomarker Staleness:
        # is_stale describes the freshness of the read snapshot/provider source (freshly built here),
        # NOT the clinical age of laboratory test observations.
        biomarker_input: BiomarkerBriefingInput | None = None
        if dashboard is not None:
            categories = getattr(dashboard, "categories", ()) or ()
            # available_count = sum of canonical biomarker summaries across categories (NOT total raw observations)
            available_count = sum(len(getattr(cat, "biomarkers", ()) or ()) for cat in categories)
            attention_count = sum(getattr(cat, "attention_count", 0) or 0 for cat in categories)

            biomarker_input = BiomarkerBriefingInput(
                available_count=available_count,
                attention_count=attention_count,
                summary=f"Większość parametrów w normie ({available_count} zweryfikowanych)"
                if attention_count == 0
                else f"Wymaga uwagi: {attention_count} marker(ów)",
                is_stale=False,
            )

        # 4. Recovery Mapping & Freshness
        recovery_input: RecoveryBriefingInput | None = None
        if (
            coach_result is not None
            and getattr(coach_result, "athlete_state", None) is not None
            and getattr(coach_result.athlete_state, "recovery", None) is not None
        ):
            rec = coach_result.athlete_state.recovery
            reasons_summary = ", ".join(rec.reasons) if getattr(rec, "reasons", None) else getattr(rec, "status", None)

            # Freshness evaluation: check source health date vs generated_at date
            is_stale = False
            context = getattr(coach_result.athlete_state, "context", None)
            today_obj = getattr(context, "today", None) if context else None
            source_date = getattr(today_obj, "date", None) if today_obj else None

            if source_date is not None:
                # Compare source date with timezone-aware generated_at date
                is_stale = (source_date != generated_at.date())

            # Helper to extract status value if present
            def _extract_status(metric_obj):
                status_val = getattr(metric_obj, "status", None) if metric_obj else None
                return status_val.value if hasattr(status_val, "value") else (str(status_val) if status_val is not None else None)

            hrv_status = _extract_status(getattr(rec, "hrv", None))
            rhr_status = _extract_status(getattr(rec, "resting_hr", None))
            sleep_status = _extract_status(getattr(rec, "sleep", None))

            recovery_input = RecoveryBriefingInput(
                score=getattr(rec, "score", None),
                status=getattr(rec, "status", None),
                summary=reasons_summary,
                is_stale=is_stale,
                hrv_status=hrv_status,
                resting_heart_rate_status=rhr_status,
                sleep_status=sleep_status,
            )

        # 5. Training Mapping
        training_input: TrainingBriefingInput | None = None
        if coach_result is not None and getattr(coach_result, "planned_workout", None) is not None:
            pw = coach_result.planned_workout
            training_input = TrainingBriefingInput(
                title=getattr(pw, "name", None),
                description=f"Sport: {getattr(pw, 'sport', '')}, Target TSS: {getattr(pw, 'target_tss', '')}",
                duration_minutes=getattr(pw, "estimated_duration", None),
                intensity=None,  # Preserved partial/None as per Stage 24.1 spec
                is_available=True,
            )
        else:
            training_input = TrainingBriefingInput(
                title=None,
                description=None,
                duration_minutes=None,
                intensity=None,
                is_available=False,
            )

        return MorningBriefingInput(
            generated_at=generated_at,
            recovery=recovery_input,
            training=training_input,
            biomarkers=biomarker_input,
        )
