from planner.catalog.aggregate import TrainingRecipe
from planner.dsl.models import Workout

from planner.dsl.workouts import (
    endurance,
    recovery,
    threshold,
    vo2,
)


class DSLParser:

    def build(
        self,
        recipe: TrainingRecipe,
    ) -> Workout:

        builders = {
            "recovery": recovery,
            "endurance": endurance,
            "threshold": threshold,
            "vo2": vo2,
        }

        try:

            builder = builders[
                recipe.identity.dsl.value
            ]

            return builder(
                recipe.prescription.duration,
                recipe.prescription.target_tss,
            )

        except KeyError as exc:

            raise ValueError(
                f"Unsupported DSL key: {recipe.identity.dsl}"
            ) from exc