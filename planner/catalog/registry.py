from planner.catalog.models import TrainingRecipe

from planner.catalog.recipes import (
    endurance_60,
    endurance_90,
    endurance_120,
    recovery_60,
    threshold_60,
    threshold_4x8,
    vo2_60,
    vo2_gorby,
)


class TrainingRecipeRegistry:

    def __init__(self) -> None:

        recipes = (
            recovery_60(),
            endurance_60(),
            endurance_90(),
            endurance_120(),
            threshold_60(),
            threshold_4x8(),
            vo2_60(),
            vo2_gorby(),
        )

        self._recipes = {
            recipe.id: recipe
            for recipe in recipes
        }

        self._by_workout_type = {}

        for recipe in recipes:

            self._by_workout_type.setdefault(
                recipe.identity.workout_type,
                [],
            ).append(recipe)

    def all(
        self,
    ) -> list[TrainingRecipe]:

        return list(
            self._recipes.values()
        )

    def by_id(
        self,
        recipe_id: str,
    ) -> TrainingRecipe:

        return self._recipes[recipe_id]

    def by_workout_type(
        self,
        workout_type,
    ) -> list[TrainingRecipe]:

        return list(
            self._by_workout_type.get(
                workout_type,
                [],
            )
        )