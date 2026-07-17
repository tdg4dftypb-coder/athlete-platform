from enum import Enum


class WorkoutType(str, Enum):
    RECOVERY = "recovery"
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    VO2 = "vo2"