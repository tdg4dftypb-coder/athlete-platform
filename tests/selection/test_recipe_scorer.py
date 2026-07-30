import pytest

from decision.prescription.models import TrainingObjective

from planner.catalog.recipes import (
    endurance_60,
    endurance_90,
    endurance_120,
    threshold_60,
    threshold_4x8,
    vo2_60,
    vo2_gorby,
)

from planner.selection.models import SelectionContext
from planner.selection.recipe_scorer import RecipeScorer


@pytest.mark.parametrize(
    (
        "available_minutes",
        "expected_recipe",
    ),
    [
        (
            60,
            "endurance_60",
        ),
        (
            75,
            "endurance_90",
        ),
        (
            90,
            "endurance_90",
        ),
        (
            100,
            "endurance_90",
        ),
        (
            120,
            "endurance_120",
        ),
        (
            180,
            "endurance_120",
        ),
    ],
)
def test_selects_best_duration(
    available_minutes: int,
    expected_recipe: str,
):

    recipes = [
        endurance_60(),
        endurance_90(),
        endurance_120(),
    ]

    context = SelectionContext(
        available_minutes=available_minutes,
        target_tss=50,
    )

    recipe = RecipeScorer().select(
        recipes,
        context,
    )

    assert recipe.id == expected_recipe


def test_selects_vo2_recipe_by_adaptation():

    recipes = [
        vo2_60(),
        vo2_gorby(),
    ]

    context = SelectionContext(
        available_minutes=75,
        target_tss=85,
        objective=TrainingObjective.VO2,
    )

    recipe = RecipeScorer().select(
        recipes,
        context,
    )

    assert recipe.id == "vo2_gorby"


def test_selects_threshold_recipe_by_adaptation():

    recipes = [
        threshold_60(),
        threshold_4x8(),
    ]

    context = SelectionContext(
        available_minutes=90,
        target_tss=80,
        objective=TrainingObjective.THRESHOLD,
    )

    recipe = RecipeScorer().select(
        recipes,
        context,
    )

    assert recipe.id == "threshold_4x8"