from dataclasses import dataclass
from enum import Enum


class EnergySystem(Enum):

    RECOVERY = "recovery"

    AEROBIC = "aerobic"

    FAT_OXIDATION = "fat_oxidation"

    TEMPO = "tempo"

    THRESHOLD = "threshold"

    VO2MAX = "vo2max"

    ANAEROBIC = "anaerobic"

    NEUROMUSCULAR = "neuromuscular"


class AdaptationTarget(Enum):

    RECOVERY = "recovery"

    AEROBIC_BASE = "aerobic_base"

    FAT_ADAPTATION = "fat_adaptation"

    TEMPO_CAPACITY = "tempo_capacity"

    FTP = "ftp"

    VO2MAX = "vo2max"

    ANAEROBIC_CAPACITY = "anaerobic_capacity"

    SPRINT_POWER = "sprint_power"

    REPEATABILITY = "repeatability"


class StressLevel(Enum):

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"


@dataclass(frozen=True, slots=True)
class TrainingStimulus:

    #
    # Primary adaptation
    #

    primary_system: EnergySystem

    adaptations: tuple[AdaptationTarget, ...]

    secondary_system: EnergySystem | None = None

    #
    # Stress profile
    #

    aerobic_stress: StressLevel = StressLevel.LOW

    muscular_stress: StressLevel = StressLevel.LOW

    metabolic_stress: StressLevel = StressLevel.LOW

    neurological_stress: StressLevel = StressLevel.LOW