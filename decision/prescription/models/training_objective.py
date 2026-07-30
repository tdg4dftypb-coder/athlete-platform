from enum import Enum


class TrainingObjective(str, Enum):

    REST = "REST"

    RECOVERY = "RECOVERY"

    ENDURANCE = "ENDURANCE"

    TEMPO = "TEMPO"

    SWEET_SPOT = "SWEET_SPOT"

    THRESHOLD = "THRESHOLD"

    VO2 = "VO2"

    ANAEROBIC = "ANAEROBIC"

    SPRINT = "SPRINT"