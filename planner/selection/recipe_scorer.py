from planner.catalog.models import TrainingRecipe
from planner.catalog.stimulus import AdaptationTarget
from planner.selection.models import SelectionContext
from decision.prescription.models import TrainingObjective


class RecipeScorer:

    OBJECTIVE_MAP = {

        TrainingObjective.RECOVERY: (
            AdaptationTarget.RECOVERY,
        ),

        TrainingObjective.REST: (
            AdaptationTarget.RECOVERY,
        ),

        TrainingObjective.ENDURANCE: (
            AdaptationTarget.AEROBIC_BASE,
        ),

        TrainingObjective.TEMPO: (
            AdaptationTarget.TEMPO_CAPACITY,
        ),

        TrainingObjective.SWEET_SPOT: (
            AdaptationTarget.TEMPO_CAPACITY,
        ),

        TrainingObjective.THRESHOLD: (
            AdaptationTarget.FTP,
        ),

        TrainingObjective.VO2: (
            AdaptationTarget.VO2MAX,
        ),

        TrainingObjective.ANAEROBIC: (
            AdaptationTarget.ANAEROBIC_CAPACITY,
        ),

        TrainingObjective.SPRINT: (
            AdaptationTarget.SPRINT_POWER,
        ),
    }


    def select(
        self,
        recipes: list[TrainingRecipe],
        context: SelectionContext,
    ) -> TrainingRecipe:

        if not recipes:

            raise ValueError(
                "No training recipes available."
            )

        return max(
            recipes,
            key=lambda recipe: self.score(
                recipe,
                context,
            ),
        )


    def score(
        self,
        recipe: TrainingRecipe,
        context: SelectionContext,
    ) -> int:

        score = 0


        #
        # Duration matching
        #

        score -= abs(
            recipe.prescription.duration
            - context.available_minutes
        )


        #
        # Training load matching
        #

        score -= abs(
            recipe.prescription.target_tss
            - context.target_tss
        )


        #
        # Recovery compatibility
        #

        if (
            context.recovery_score
            >= recipe.selection.min_recovery_score
        ):

            score += 20

        else:

            score -= 50


        #
        # Fatigue compatibility
        #

        if (
            context.fatigue_score
            <= recipe.selection.max_fatigue_score
        ):

            score += 20

        else:

            score -= 50


        #
        # Adaptation objective matching
        #

        if context.objective:

            targets = self.OBJECTIVE_MAP.get(
                context.objective,
                (),
            )

            if any(
                adaptation in recipe.stimulus.adaptations
                for adaptation in targets
            ):

                score += 30

            else:

                score -= 10


        #
        # Stimulus quality
        #

        if recipe.stimulus.primary_system:

            score += 5


        #
        # Analytics awareness
        #

        if recipe.analytics.fatigue_index < 0.8:

            score += 5


        return score