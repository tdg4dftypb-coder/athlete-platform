from planning.models import (
    PlannedDay,
    WeeklyPlan,
)


class PlanningEngine:

    def build(self) -> WeeklyPlan:

        return WeeklyPlan(

            days=[

                PlannedDay(
                    day="MON",
                    workout="Recovery",
                    duration=45,
                    target_tss=25,
                ),

                PlannedDay(
                    day="TUE",
                    workout="Tempo",
                    duration=90,
                    target_tss=70,
                ),

                PlannedDay(
                    day="WED",
                    workout="Recovery",
                    duration=45,
                    target_tss=25,
                ),

                PlannedDay(
                    day="THU",
                    workout="VO2",
                    duration=75,
                    target_tss=95,
                ),

                PlannedDay(
                    day="FRI",
                    workout="OFF",
                    duration=0,
                    target_tss=0,
                ),

                PlannedDay(
                    day="SAT",
                    workout="Long Ride",
                    duration=180,
                    target_tss=180,
                ),

                PlannedDay(
                    day="SUN",
                    workout="Endurance",
                    duration=120,
                    target_tss=90,
                ),

            ]

        )