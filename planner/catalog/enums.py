from enum import Enum


class WorkoutTag(Enum):

    FTP = "ftp"
    STEADY_STATE = "steady_state"
    RECOVERY = "recovery"
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    VO2 = "vo2"
    CADENCE = "cadence"
    SWEET_SPOT = "sweet_spot"


class LoadLevel(Enum):

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TerrainType(Enum):

    ROAD = "road"
    GRAVEL = "gravel"
    MTB = "mtb"
    INDOOR = "indoor"


class CadenceType(Enum):

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class FuelStrategy(Enum):

    CARB = "carb"
    MIXED = "mixed"
    FAT_ADAPTATION = "fat_adaptation"


class RideProfile(Enum):

    STEADY = "steady"
    VARIABLE = "variable"
    CLIMBING = "climbing"