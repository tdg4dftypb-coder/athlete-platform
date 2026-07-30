from planner.catalog.models import TrainingRecipe
from planner.selection.models import SelectionContext


class RecipeFilter:

    def by_available_time(
        self,
        recipes: list[TrainingRecipe],
        context: SelectionContext,
    ) -> list[TrainingRecipe]:

        return [
            recipe
            for recipe in recipes
            if (
                recipe.prescription.duration
                <= context.available_minutes
            )
        ]

    def filter(
        self,
        recipes: list[TrainingRecipe],
        context: SelectionContext,
    ) -> list[TrainingRecipe]:

        return [
            recipe
            for recipe in recipes
            if self._matches(
                recipe,
                context,
            )
        ]

    def _matches(
        self,
        recipe: TrainingRecipe,
        context: SelectionContext,
    ) -> bool:

        return (
            self._matches_duration(
                recipe,
                context,
            )
            and self._matches_recovery(
                recipe,
                context,
            )
            and self._matches_fatigue(
                recipe,
                context,
            )
        )

    def _matches_duration(
        self,
        recipe: TrainingRecipe,
        context: SelectionContext,
    ) -> bool:

        duration = recipe.prescription.duration

        return (
            duration <= context.available_minutes
            and duration >= recipe.selection.min_duration
            and duration <= recipe.selection.max_duration
        )

    def _matches_recovery(
        self,
        recipe: TrainingRecipe,
        context: SelectionContext,
    ) -> bool:

        if not hasattr(context, "recovery_score"):
            return True

        return (
            context.recovery_score
            >= recipe.selection.min_recovery_score
        )

    def _matches_fatigue(
        self,
        recipe: TrainingRecipe,
        context: SelectionContext,
    ) -> bool:

        if not hasattr(context, "fatigue_score"):
            return True

        return (
            context.fatigue_score
            <= recipe.selection.max_fatigue_score
        )