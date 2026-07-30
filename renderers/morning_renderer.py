class MorningRenderer:

    def render(
        self,
        recovery,
        performance,
        last_workout,
        context,
        decision,
    ):

        self._render_recovery(recovery)

        self._render_performance(performance)

        self._render_last_workout(last_workout)

        self._render_metrics(context)

        self._render_decision(decision)

    def _render_recovery(
        self,
        recovery,
    ):

        print("Recovery")
        print("-" * 72)

        print(f"Score      : {recovery.score}/100")
        print(f"Status     : {recovery.status}")

        if recovery.reasons:

            print()
            print("Reasons")

            for reason in recovery.reasons:
                print(f" • {reason}")

        print()

    def _render_performance(
        self,
        performance,
    ):

        print("Performance")
        print("-" * 72)

        print(f"ATL        : {performance.atl:.1f}")
        print(f"CTL        : {performance.ctl:.1f}")
        print(f"TSB        : {performance.tsb:.1f}")

        print()

        print(f"7d Workouts: {performance.weekly.workouts}")
        print(f"7d TSS     : {performance.weekly.total_tss:.0f}")
        print(f"Avg TSS    : {performance.weekly.average_tss:.1f}")

        print()

    def _render_last_workout(
        self,
        last_workout,
    ):

        print("Last Workout")
        print("-" * 72)

        if last_workout:

            duration = last_workout[4]

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            if hours:
                duration_text = f"{hours} h {minutes:02d} min"
            else:
                duration_text = f"{minutes} min {seconds:02d} s"

            print(f"Sport      : {last_workout[3]}")
            print(f"Duration   : {duration_text}")
            print(f"TSS        : {last_workout[11]:.1f}")

        else:

            print("Brak treningów.")

        print()

    def _render_metrics(
        self,
        context,
    ):

        sleep = context.today.sleep_duration

        hours = sleep // 60
        minutes = sleep % 60

        print("Today's Metrics")
        print("-" * 72)

        print(f"HRV        : {context.today.hrv:.1f}")
        print(f"RHR        : {context.today.resting_hr:.1f}")
        print(f"Sleep      : {hours} h {minutes:02d} min")
        print(f"Steps      : {int(context.today.steps)}")

        print()

    def _render_decision(
        self,
        plan,
    ):

        print("Today's Recommendation")
        print("-" * 72)

        if not plan.results:
            print("Brak rekomendacji.")
            print()
            return

        decision = plan.results[0]

        print(f"Sport      : {decision.sport.value}")
        print(f"Workout    : {decision.recommendation.value}")
        print(f"Duration   : {decision.duration} min")
        print(f"Target TSS : {decision.target_tss:.0f}")
        print(f"Intensity  : {decision.intensity}")
        print(f"Confidence : {decision.confidence:.0f}%")

        if decision.reasons:

            print()
            print("Reasons")

            for reason in decision.reasons:
                print(f" • {reason}")

        print()