from planner.models import (
    PlannedBlock,
    PlannedWorkout,
)


class WorkoutLibrary:

    @staticmethod
    def recovery():

        return PlannedWorkout(

            name="Recovery Ride",

            sport="cycling",

            target_tss=25,

            estimated_duration=45,

            blocks=[

                PlannedBlock(

                    name="Recovery",

                    duration=45 * 60,

                    power_from=0.45,

                    power_to=0.55,

                    cadence_from=85,

                    cadence_to=95,

                )

            ],

        )

    @staticmethod
    def endurance():

        return PlannedWorkout(

            name="Endurance Ride",

            sport="cycling",

            target_tss=55,

            estimated_duration=90,

            blocks=[

                PlannedBlock(

                    name="Endurance",

                    duration=90 * 60,

                    power_from=0.60,

                    power_to=0.75,

                    cadence_from=85,

                    cadence_to=95,

                )

            ],

        )

    @staticmethod
    def tempo():

        return PlannedWorkout(

            name="Tempo Ride",

            sport="cycling",

            target_tss=70,

            estimated_duration=90,

            blocks=[

                PlannedBlock(

                    name="Warmup",

                    duration=15 * 60,

                    power_from=0.50,

                    power_to=0.70,

                    cadence_from=85,

                    cadence_to=95,

                ),

                PlannedBlock(

                    name="Tempo",

                    duration=60 * 60,

                    power_from=0.80,

                    power_to=0.88,

                    cadence_from=90,

                    cadence_to=100,

                ),

                PlannedBlock(

                    name="Cooldown",

                    duration=15 * 60,

                    power_from=0.45,

                    power_to=0.60,

                    cadence_from=80,

                    cadence_to=90,

                ),

            ],

        )

    @staticmethod
    def threshold():

        return PlannedWorkout(

            name="Threshold Ride",

            sport="cycling",

            target_tss=90,

            estimated_duration=75,

            blocks=[],

        )

    @staticmethod
    def vo2():

        return PlannedWorkout(

            name="VO2 Ride",

            sport="cycling",

            target_tss=100,

            estimated_duration=75,

            blocks=[],

        )