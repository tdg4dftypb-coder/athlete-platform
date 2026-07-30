from athlete.models import AthleteState
from briefing.models import MorningBriefing
from coach.models import CoachRecommendation
from decision.models import DecisionResult


class MorningBriefingBuilder:

    def build(
        self,
        athlete: AthleteState,
        decision: DecisionResult,
        coach: CoachRecommendation,
    ) -> MorningBriefing:

        today = athlete.health.today

        workout = athlete.last_workout

        return MorningBriefing(

            #
            # Date
            #

            date=str(today.date),

            #
            # Recovery
            #

            recovery_score=athlete.recovery.score,

            recovery_status=athlete.recovery.status,

            #
            # Performance
            #

            performance=athlete.performance,

            #
            # Decision
            #

            decision=decision,

            #
            # Coach
            #

            recommendation=coach,

            #
            # Health
            #

            hrv=today.hrv,

            resting_hr=today.resting_hr,

            sleep_minutes=today.sleep_duration,

            steps=today.steps,

            #
            # Last workout
            #

            workout_duration=(
                workout.duration
                if workout
                else 0
            ),

            workout_avg_power=(
                round(workout.average_power)
                if workout
                else 0
            ),

            workout_np=(
                round(workout.normalized_power)
                if workout
                else 0
            ),

            workout_avg_hr=(
                round(workout.average_hr)
                if workout
                else 0
            ),
        )