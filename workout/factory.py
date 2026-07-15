from decision.models import DecisionState

from workout.templates import (
    EnduranceTemplate,
    RecoveryTemplate,
    SprintTemplate,
    TempoTemplate,
    ThresholdTemplate,
    VO2Template,
)


class WorkoutFactory:

    def create(
        self,
        decision: DecisionState,
    ):

        if decision.recommendation == "REST":

            return None

        if decision.recommendation == "RECOVERY":

            return RecoveryTemplate(

                name="Recovery Ride",

                goal="Recovery",

                description="Lekka jazda regeneracyjna.",

                duration=decision.duration,

                target_if=0.50,

                target_tss=decision.target_tss,

            )

        if decision.recommendation == "ENDURANCE":

            return EnduranceTemplate(

                name="Endurance Ride",

                goal="Aerobic Endurance",

                description="Rozwój wytrzymałości tlenowej.",

                duration=decision.duration,

                target_if=0.65,

                target_tss=decision.target_tss,

            )

        if decision.recommendation == "TEMPO":

            return TempoTemplate(

                name="Tempo Ride",

                goal="Tempo",

                description="Rozwój wytrzymałości tempowej.",

                duration=decision.duration,

                target_if=0.80,

                target_tss=decision.target_tss,

            )

        if decision.recommendation == "THRESHOLD":

            return ThresholdTemplate(

                name="Threshold",

                goal="FTP",

                description="Rozwój mocy progowej.",

                duration=decision.duration,

                target_if=0.92,

                target_tss=decision.target_tss,

            )

        if decision.recommendation == "VO2":

            return VO2Template(

                name="VO2 Builder",

                goal="VO2max",

                description="Interwały VO₂max.",

                duration=decision.duration,

                target_if=0.95,

                target_tss=decision.target_tss,

            )

        if decision.recommendation == "SPRINT":

            return SprintTemplate(

                name="Sprint Builder",

                goal="Neuromuscular",

                description="Trening sprintów.",

                duration=decision.duration,

                target_if=0.90,

                target_tss=decision.target_tss,

            )

        raise ValueError(
            f"Unknown workout recommendation: {decision.recommendation}"
        )