"""Production runtime adapter for closed-date activity reconciliation."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from activity_reconciliation.service import ActivitySessionReconciler
from production_runtime.coordinator import RuntimePhaseContext, RuntimePhaseOutcome
from production_runtime.models import PhaseStatus, RuntimeWarning


RECONCILIATION_PLAN_UNAVAILABLE = "reconciliation_plan_unavailable"


class ProductionReconciliationAdapter:
    """Reconciles only the previous closed local date using persisted facts."""

    def __init__(
        self,
        training_plan_repository,
        athlete_memory_repository,
        reconciliation_repository,
        reconciler: ActivitySessionReconciler,
        clock,
        timezone_name: str,
    ) -> None:
        self._plans = training_plan_repository
        self._memory = athlete_memory_repository
        self._results = reconciliation_repository
        self._reconciler = reconciler
        self._clock = clock
        self._timezone_name = timezone_name

    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome:
        reconciliation_date = context.target_local_date - timedelta(days=1)
        plan = self._plans.get_for_date(reconciliation_date)
        if plan is None:
            return RuntimePhaseOutcome(
                status=PhaseStatus.SKIPPED,
                warning_codes=(RECONCILIATION_PLAN_UNAVAILABLE,),
                warnings=(RuntimeWarning(
                    RECONCILIATION_PLAN_UNAVAILABLE,
                    f"No training plan covers {reconciliation_date.isoformat()}",
                    "reconciliation",
                ),),
                reconciliations_created=0,
            )

        # occurred_at is the activity end. A one-day margin on both sides is
        # bounded and covers local/UTC offsets plus activities crossing midnight;
        # the reconciler filters authoritatively by payload activity start.
        query_start = datetime.combine(reconciliation_date - timedelta(days=1), time.min)
        query_end = datetime.combine(reconciliation_date + timedelta(days=2), time.min)
        activities = tuple(self._memory.load_between(query_start, query_end))
        result = self._reconciler.reconcile(
            plan=plan,
            activities=activities,
            target_date=reconciliation_date,
            finalized=True,
            evaluated_at=self._clock.now_utc(),
            timezone_name=self._timezone_name,
        )
        created = self._results.save(result)
        return RuntimePhaseOutcome(
            changed_state=created,
            item_count=len(result.items),
            artifact_ids=(result.reconciliation_id,),
            reconciliations_created=1 if created else 0,
        )
