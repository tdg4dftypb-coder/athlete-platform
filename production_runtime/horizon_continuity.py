"""Runtime adapter for same-plan horizon continuity."""
from datetime import timedelta

from production_runtime.coordinator import RuntimePhaseError, RuntimePhaseOutcome
from training_plan.continuity import HorizonExtensionStatus, TrainingPlanHorizonExtensionService
from training_plan.repository import TrainingPlanConflictError, TrainingPlanDataError


CONTINUATION_SPECIFICATION_UNAVAILABLE = "continuation_specification_unavailable"
CONTINUATION_CONFLICT = "continuation_conflict"


class PlanHorizonContinuityAdapter:
    def __init__(self, plans, clock, extension_service=None):
        self.plans=plans; self.clock=clock
        self.extension_service=extension_service or TrainingPlanHorizonExtensionService()

    def execute(self, context):
        plan_id=context.result.training_plan_id
        if not plan_id: raise RuntimePhaseError("missing_training_plan")
        source=self.plans.get_by_id(plan_id)
        if source is None: raise RuntimePhaseError("missing_training_plan")
        specification=self.plans.get_latest_continuation_specification_for_plan(source.plan_id)
        if specification is None:
            minimum=context.target_local_date+timedelta(days=7)
            if source.end_date >= minimum:
                return RuntimePhaseOutcome(artifact_ids=(self.artifact_id(source),),training_plan_id=source.plan_id)
            raise RuntimePhaseError(CONTINUATION_SPECIFICATION_UNAVAILABLE)
        required=context.target_local_date+timedelta(days=specification.target_horizon_days)
        if source.end_date >= required:
            return RuntimePhaseOutcome(artifact_ids=(self.artifact_id(source),),training_plan_id=source.plan_id)
        result=self.extension_service.extend(source,specification,required,generated_at=self.clock.now_utc())
        try:
            changed=self.plans.append_revision(source.version,result.plan)
        except (TrainingPlanConflictError,TrainingPlanDataError) as error:
            raise RuntimePhaseError(CONTINUATION_CONFLICT,str(error)) from error
        persisted=self.plans.get_by_id_version(result.plan.plan_id,result.plan.version)
        if persisted != result.plan: raise RuntimePhaseError("continuation_result_unresolvable")
        return RuntimePhaseOutcome(changed_state=changed,artifact_ids=(self.artifact_id(persisted),),training_plan_id=persisted.plan_id)

    @staticmethod
    def artifact_id(plan): return f"training-plan:{plan.plan_id}:v{plan.version}"
