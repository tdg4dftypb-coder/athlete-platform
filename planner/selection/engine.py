from planner.catalog.models import TrainingRecipe
from planner.catalog.registry import TrainingRecipeRegistry
from planner.selection.filter import RecipeFilter
from planner.selection.models import SelectionContext
from planner.selection.recipe_scorer import RecipeScorer
from workout.enums import WorkoutType


class SelectionEngine:

    def __init__(self):

        self._registry = TrainingRecipeRegistry()

        self._filter = RecipeFilter()

        self._scorer = RecipeScorer()


    def select(
        self,
        workout_type: WorkoutType,
        context: SelectionContext,
    ) -> TrainingRecipe:

        candidates = self._registry.by_workout_type(
            workout_type,
        )

        candidates = self._filter.filter(
            candidates,
            context,
        )

        if not candidates:

            raise ValueError(
                "No training recipes match the selection criteria."
            )

        return self._scorer.select(
            candidates,
            context,
        )