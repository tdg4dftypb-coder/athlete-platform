from core.results import MorningBriefing


class MorningBriefingPrinter:

    def print(self, briefing: MorningBriefing):

        print()
        print("=" * 40)
        print("MORNING BRIEFING")
        print("=" * 40)

        # ===================================
        # 1. Stan organizmu
        # ===================================

        print()
        print("1. Stan organizmu")
        print("-" * 25)

        print(briefing.readiness.status)
        print()
        print(briefing.readiness.explanation)

        # ===================================
        # 2. Bilans energetyczny
        # ===================================

        if briefing.energy_balance:

            print()
            print("2. Bilans energetyczny")
            print("-" * 25)

            print(briefing.energy_balance.status)
            print()
            print(briefing.energy_balance.explanation)

        # ===================================
        # 3. Cel długoterminowy
        # ===================================

        if briefing.long_term:

            print()
            print("3. Cel długoterminowy")
            print("-" * 25)

            print(briefing.long_term.status)
            print()
            print(briefing.long_term.explanation)

        # ===================================
        # 4. Najważniejsza rekomendacja
        # ===================================

        print()
        print("4. Najważniejsza rekomendacja")
        print("-" * 25)

        print(briefing.recommendation)

        # ===================================
        # 5. Alerty
        # ===================================

        if briefing.alerts:

            print()
            print("5. Alerty")
            print("-" * 25)

            for alert in briefing.alerts:

                print(f"[{alert.severity}] {alert.title}")
                print(alert.message)
                print()