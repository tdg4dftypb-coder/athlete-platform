class ConsoleRenderer:

    def render(self, briefing):

        print()
        print("=" * 72)
        print("ATHLETE PLATFORM")
        print("=" * 72)
        print()

        print(
            f"Recovery : "
            f"{briefing.recovery.score}/100"
        )

        print(
            f"Status   : "
            f"{briefing.recovery.status}"
        )

        print()

        print(
            f"ATL      : "
            f"{briefing.performance.atl:.1f}"
        )

        print(
            f"CTL      : "
            f"{briefing.performance.ctl:.1f}"
        )

        print(
            f"TSB      : "
            f"{briefing.performance.tsb:.1f}"
        )

        print()