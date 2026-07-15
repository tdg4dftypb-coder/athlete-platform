from dataclasses import dataclass


@dataclass
class CoachRecommendation:

    title: str

    workout_type: str

    message: str

    reasons: list[str]