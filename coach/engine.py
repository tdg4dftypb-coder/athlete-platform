from athlete.models import AthleteState
from coach.models import CoachRecommendation
from decision.models import DecisionState


class CoachEngine:

    def recommend(
        self,
        athlete: AthleteState,
        decision: DecisionState,
    ) -> CoachRecommendation:

        reasons = []

        reasons.extend(athlete.recovery.reasons)
        reasons.extend(decision.reasons)

        if decision.recommendation == "REST":

            return CoachRecommendation(

                title="🔴 Odpoczynek",

                workout_type="REST",

                message=(
                    "Organizm potrzebuje regeneracji. "
                    "Najlepszą decyzją będzie dzień odpoczynku."
                ),

                reasons=reasons,
            )

        if decision.recommendation == "RECOVERY":

            return CoachRecommendation(

                title="🟠 Trening regeneracyjny",

                workout_type="RECOVERY",

                message=(
                    f"Wykonaj lekką jazdę regeneracyjną "
                    f"przez {decision.duration} minut."
                ),

                reasons=reasons,
            )

        if decision.recommendation == "ENDURANCE":

            return CoachRecommendation(

                title="🟡 Trening wytrzymałościowy",

                workout_type="ENDURANCE",

                message=(
                    f"Wykonaj spokojną jazdę w strefie "
                    f"{decision.intensity} przez "
                    f"{decision.duration} minut. "
                    f"Cel: około {decision.target_tss:.0f} TSS."
                ),

                reasons=reasons,
            )

        if decision.recommendation == "TEMPO":

            return CoachRecommendation(

                title="🟡 Trening Tempo",

                workout_type="TEMPO",

                message=(
                    f"Wykonaj trening Tempo "
                    f"({decision.duration} min, "
                    f"{decision.target_tss:.0f} TSS)."
                ),

                reasons=reasons,
            )

        if decision.recommendation == "VO2":

            return CoachRecommendation(

                title="🟢 Trening VO₂",

                workout_type="VO2",

                message=(
                    f"Organizm jest gotowy na mocny trening. "
                    f"Wykonaj jednostkę VO₂ "
                    f"({decision.duration} min, "
                    f"{decision.target_tss:.0f} TSS)."
                ),

                reasons=reasons,
            )

        return CoachRecommendation(

            title="ℹ️ Brak rekomendacji",

            workout_type="NONE",

            message="Brak decyzji treningowej.",

            reasons=reasons,
        )