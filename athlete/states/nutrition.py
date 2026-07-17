from dataclasses import dataclass


@dataclass
class NutritionState:

    calories: float = 0

    carbohydrates: float = 0

    protein: float = 0

    fat: float = 0

    hydration: float = 0