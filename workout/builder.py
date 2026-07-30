from decision.models import DecisionResult

from workout.blocks import (
    CooldownBlock,
    EnduranceBlock,
    RecoveryBlock,
    TempoBlock,
    ThresholdBlock,
    VO2Block,
    WarmupBlock,
)

from workout.factory import WorkoutFactory
from workout.models import Workout
from workout.templates import (
    EnduranceTemplate,
    RecoveryTemplate,
    TempoTemplate,
    ThresholdTemplate,
    VO2Template,
)


class WorkoutBuilder:

    def __init__(self):

        self.factory = WorkoutFactory()

    def build(
        self,
        decision: DecisionResult,
    ) -> Workout:

        template = self.factory.create(decision)

        if template is None:

            return Workout(

                name="Rest Day",

                goal="Recovery",

                description="Complete rest.",

                duration=0,

                target_tss=0,

                target_if=0,

                blocks=[],

            )

        if isinstance(template, RecoveryTemplate):

            return self._build_recovery(template)

        if isinstance(template, EnduranceTemplate):

            return self._build_endurance(template)

        if isinstance(template, TempoTemplate):

            return self._build_tempo(template)

        if isinstance(template, ThresholdTemplate):

            return self._build_threshold(template)

        if isinstance(template, VO2Template):

            return self._build_vo2(template)

        raise ValueError("Unsupported template.")

    def _build_recovery(
        self,
        template: RecoveryTemplate,
    ) -> Workout:

        return Workout(

            name=template.name,

            goal=template.goal,

            description=template.description,

            duration=template.duration,

            target_tss=template.target_tss,

            target_if=template.target_if,

            blocks=[

                WarmupBlock(

                    name="Warmup",

                    description="Easy spin.",

                    duration=300,

                    power_from=0.40,

                    power_to=0.55,

                    cadence_from=85,

                    cadence_to=95,

                ),

                RecoveryBlock(

                    name="Recovery",

                    description="Easy endurance.",

                    duration=(template.duration * 60) - 600,

                    power_from=0.50,

                    power_to=0.55,

                    cadence_from=90,

                    cadence_to=100,

                ),

                CooldownBlock(

                    name="Cooldown",

                    description="Cooldown.",

                    duration=300,

                    power_from=0.35,

                    power_to=0.45,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )

    def _build_endurance(
        self,
        template: EnduranceTemplate,
    ) -> Workout:

        return Workout(

            name=template.name,

            goal=template.goal,

            description=template.description,

            duration=template.duration,

            target_tss=template.target_tss,

            target_if=template.target_if,

            blocks=[

                WarmupBlock(

                    name="Warmup",

                    description="Progressive warmup.",

                    duration=600,

                    power_from=0.45,

                    power_to=0.60,

                    cadence_from=85,

                    cadence_to=95,

                ),

                EnduranceBlock(

                    name="Endurance",

                    description="Steady endurance.",

                    duration=(template.duration * 60) - 900,

                    power_from=0.65,

                    power_to=0.70,

                    cadence_from=90,

                    cadence_to=100,

                ),

                CooldownBlock(

                    name="Cooldown",

                    description="Easy finish.",

                    duration=300,

                    power_from=0.40,

                    power_to=0.45,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )

    def _build_tempo(
        self,
        template: TempoTemplate,
    ) -> Workout:

        return Workout(

            name=template.name,

            goal=template.goal,

            description=template.description,

            duration=template.duration,

            target_tss=template.target_tss,

            target_if=template.target_if,

            blocks=[

                WarmupBlock(

                    name="Warmup",

                    description="Warmup.",

                    duration=600,

                    power_from=0.45,

                    power_to=0.60,

                    cadence_from=85,

                    cadence_to=95,

                ),

                TempoBlock(

                    name="Tempo",

                    description="Tempo effort.",

                    duration=(template.duration * 60) - 900,

                    power_from=0.78,

                    power_to=0.85,

                    cadence_from=90,

                    cadence_to=100,

                ),

                CooldownBlock(

                    name="Cooldown",

                    description="Cooldown.",

                    duration=300,

                    power_from=0.40,

                    power_to=0.45,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )

    def _build_threshold(
        self,
        template: ThresholdTemplate,
    ) -> Workout:

        return Workout(

            name=template.name,

            goal=template.goal,

            description=template.description,

            duration=template.duration,

            target_tss=template.target_tss,

            target_if=template.target_if,

            blocks=[

                WarmupBlock(

                    name="Warmup",

                    description="Warmup.",

                    duration=900,

                    power_from=0.45,

                    power_to=0.60,

                    cadence_from=85,

                    cadence_to=95,

                ),

                ThresholdBlock(

                    name="Threshold",

                    description="FTP effort.",

                    duration=(template.duration * 60) - 1200,

                    power_from=0.95,

                    power_to=1.00,

                    cadence_from=90,

                    cadence_to=100,

                ),

                CooldownBlock(

                    name="Cooldown",

                    description="Cooldown.",

                    duration=300,

                    power_from=0.40,

                    power_to=0.45,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )

    def _build_vo2(
        self,
        template: VO2Template,
    ) -> Workout:

        return Workout(

            name=template.name,

            goal=template.goal,

            description=template.description,

            duration=template.duration,

            target_tss=template.target_tss,

            target_if=template.target_if,

            blocks=[

                WarmupBlock(

                    name="Warmup",

                    description="Warmup.",

                    duration=900,

                    power_from=0.45,

                    power_to=0.60,

                    cadence_from=85,

                    cadence_to=95,

                ),

                VO2Block(

                    name="VO2",

                    description="VO2 intervals.",

                    duration=1200,

                    power_from=1.10,

                    power_to=1.20,

                    cadence_from=95,

                    cadence_to=105,

                    repeat=2,

                ),

                RecoveryBlock(

                    name="Recovery",

                    description="Easy spin.",

                    duration=300,

                    power_from=0.45,

                    power_to=0.55,

                    cadence_from=85,

                    cadence_to=95,

                ),

                CooldownBlock(

                    name="Cooldown",

                    description="Cooldown.",

                    duration=600,

                    power_from=0.40,

                    power_to=0.45,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )