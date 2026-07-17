from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionMatrix:

    #
    # Recovery
    #

    REST = 40

    RECOVERY = 60

    GOOD = 80

    #
    # Performance
    #

    FATIGUE = -10

    FRESH = 10

    #
    # Workouts
    #

    RECOVERY_DURATION = 45
    ENDURANCE_DURATION = 90
    TEMPO_DURATION = 90
    THRESHOLD_DURATION = 75
    VO2_DURATION = 75

    RECOVERY_TSS = 25
    ENDURANCE_TSS = 55
    TEMPO_TSS = 70
    THRESHOLD_TSS = 90
    VO2_TSS = 100