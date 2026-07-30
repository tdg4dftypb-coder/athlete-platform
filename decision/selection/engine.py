from decision.models import (
    DecisionResult,
    WorkoutPlan,
)
from decision.prescription.models import (
    TrainingObjective,
    TrainingPrescription,
)
from decision.sports import Sport
from workout.enums import WorkoutType


class SelectionEngine:

    def select(
        self,
        prescription: TrainingPrescription,
    ) -> WorkoutPlan:

        plan = WorkoutPlan()

        mapping = {
            TrainingObjective.REST: WorkoutType.RECOVERY,
            TrainingObjective.RECOVERY: WorkoutType.RECOVERY,
            TrainingObjective.ENDURANCE: WorkoutType.ENDURANCE,
            TrainingObjective.TEMPO: WorkoutType.TEMPO,
            TrainingObjective.SWEET_SPOT: WorkoutType.TEMPO,
            TrainingObjective.THRESHOLD: WorkoutType.THRESHOLD,
            TrainingObjective.VO2: WorkoutType.VO2,
            TrainingObjective.ANAEROBIC: WorkoutType.VO2,
            TrainingObjective.SPRINT: WorkoutType.VO2,
        }

        duration = prescription.duration_minutes

        target_tss = prescription.target_tss

        if duration > 0:
            load_rate = round(
                target_tss * 60 / duration
            )
        else:
            load_rate = 0

        result = DecisionResult(
            sport=Sport.CYCLING,

            recommendation=mapping[
                prescription.objective
            ],

            objective=prescription.objective,

            duration=duration,

            target_tss=target_tss,

            intensity=f"{load_rate} TSS/h",

            reasons=list(
                prescription.reasons,
            ),

            priority=prescription.priority,

            confidence=prescription.confidence,

            source_rules=[
                "SelectionEngine",
            ],
        )

        plan.add_result(
            result,
        )

        return plan