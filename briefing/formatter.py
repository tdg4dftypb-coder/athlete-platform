from briefing.models import MorningBriefing


class ConsoleFormatter:

    def print(
        self,
        briefing: MorningBriefing,
    ):

        print()

        print("=" * 60)
        print("ATHLETE PLATFORM")
        print("=" * 60)

        print()

        print(briefing.date)

        print()

        print(
            f"Recovery : "
            f"{briefing.recovery_score}/100"
        )

        print(
            f"Status    : "
            f"{briefing.recovery_status}"
        )

        print()

        print(
            briefing.recommendation.title
        )

        print(
            briefing.recommendation.message
        )

        print()

        print("Today's metrics")

        print(
            f"HRV      : {briefing.hrv}"
        )

        print(
            f"RHR      : {briefing.resting_hr}"
        )

        print(
            f"Sleep    : "
            f"{briefing.sleep_minutes} min"
        )

        print(
            f"Steps    : {briefing.steps}"
        )

        print()

        print("Yesterday workout")

        print(
            f"Duration : "
            f"{briefing.workout_duration // 60} min"
        )

        print(
            f"Avg Power: "
            f"{briefing.workout_avg_power} W"
        )

        print(
            f"NP       : "
            f"{briefing.workout_np} W"
        )

        print(
            f"Avg HR   : "
            f"{briefing.workout_avg_hr} bpm"
        )

        print()

        print("Reasons")

        for reason in briefing.recommendation.reasons:

            print(f" • {reason}")

        print()

        print("Recommendation")

        print(
            briefing.recommendation.workout_type
        )

        print()