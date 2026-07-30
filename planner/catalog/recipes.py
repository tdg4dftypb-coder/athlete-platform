from planner.catalog.analytics import AnalyticsProfile
from planner.catalog.identity import TrainingIdentity
from planner.catalog.models import TrainingRecipe
from planner.catalog.prescription import WorkoutPrescription
from planner.catalog.selection import SelectionProfile
from planner.catalog.stimulus import (
    AdaptationTarget,
    EnergySystem,
    StressLevel,
    TrainingStimulus,
)

from workout.enums import WorkoutType


def recovery() -> TrainingRecipe:

    return recovery_60()


def endurance() -> TrainingRecipe:

    return endurance_120()


def threshold() -> TrainingRecipe:

    return threshold_4x8()


def vo2() -> TrainingRecipe:

    return vo2_gorby()


def build_recipe(
    *,
    id: str,
    name: str,
    workout_type: WorkoutType,
    duration: int,
    target_tss: float,
    primary_system: EnergySystem,
    adaptations: tuple[AdaptationTarget, ...],
    interval_structure: str,
    min_duration: int,
    max_duration: int,
    aerobic_stress: StressLevel,
    muscular_stress: StressLevel,
    metabolic_stress: StressLevel,
    neurological_stress: StressLevel,
) -> TrainingRecipe:

    return TrainingRecipe(
        identity=TrainingIdentity(
            id=id,
            name=name,
            workout_type=workout_type,
            dsl=workout_type,
        ),

        stimulus=TrainingStimulus(
            primary_system=primary_system,
            adaptations=adaptations,
            aerobic_stress=aerobic_stress,
            muscular_stress=muscular_stress,
            metabolic_stress=metabolic_stress,
            neurological_stress=neurological_stress,
        ),

        prescription=WorkoutPrescription(
            duration=duration,
            target_tss=target_tss,
            interval_structure=interval_structure,
        ),

        selection=SelectionProfile(
            min_duration=min_duration,
            max_duration=max_duration,
        ),

        analytics=AnalyticsProfile(
            aerobic_load=aerobic_stress,
            muscular_load=muscular_stress,
            metabolic_load=metabolic_stress,
            neurological_load=neurological_stress,
            fatigue_index=target_tss / 100,
        ),
    )


def recovery_60() -> TrainingRecipe:

    return build_recipe(
        id="recovery_60",
        name="Recovery 60",
        workout_type=WorkoutType.RECOVERY,
        duration=60,
        target_tss=25,
        primary_system=EnergySystem.RECOVERY,
        adaptations=(
            AdaptationTarget.RECOVERY,
        ),
        interval_structure="steady",
        min_duration=45,
        max_duration=90,
        aerobic_stress=StressLevel.LOW,
        muscular_stress=StressLevel.LOW,
        metabolic_stress=StressLevel.LOW,
        neurological_stress=StressLevel.LOW,
    )


def endurance_60() -> TrainingRecipe:

    return build_recipe(
        id="endurance_60",
        name="Endurance 60",
        workout_type=WorkoutType.ENDURANCE,
        duration=60,
        target_tss=35,
        primary_system=EnergySystem.AEROBIC,
        adaptations=(
            AdaptationTarget.AEROBIC_BASE,
        ),
        interval_structure="steady",
        min_duration=45,
        max_duration=120,
        aerobic_stress=StressLevel.MEDIUM,
        muscular_stress=StressLevel.LOW,
        metabolic_stress=StressLevel.MEDIUM,
        neurological_stress=StressLevel.LOW,
    )


def endurance_90() -> TrainingRecipe:

    return build_recipe(
        id="endurance_90",
        name="Endurance 90",
        workout_type=WorkoutType.ENDURANCE,
        duration=90,
        target_tss=50,
        primary_system=EnergySystem.AEROBIC,
        adaptations=(
            AdaptationTarget.AEROBIC_BASE,
        ),
        interval_structure="steady",
        min_duration=60,
        max_duration=180,
        aerobic_stress=StressLevel.MEDIUM,
        muscular_stress=StressLevel.LOW,
        metabolic_stress=StressLevel.MEDIUM,
        neurological_stress=StressLevel.LOW,
    )


def endurance_120() -> TrainingRecipe:

    return build_recipe(
        id="endurance_120",
        name="Endurance 120",
        workout_type=WorkoutType.ENDURANCE,
        duration=120,
        target_tss=65,
        primary_system=EnergySystem.AEROBIC,
        adaptations=(
            AdaptationTarget.AEROBIC_BASE,
            AdaptationTarget.FAT_ADAPTATION,
        ),
        interval_structure="steady",
        min_duration=90,
        max_duration=240,
        aerobic_stress=StressLevel.HIGH,
        muscular_stress=StressLevel.LOW,
        metabolic_stress=StressLevel.MEDIUM,
        neurological_stress=StressLevel.LOW,
    )


def threshold_60() -> TrainingRecipe:

    return build_recipe(
        id="threshold_60",
        name="Threshold 60",
        workout_type=WorkoutType.THRESHOLD,
        duration=60,
        target_tss=75,
        primary_system=EnergySystem.THRESHOLD,
        adaptations=(
            AdaptationTarget.FTP,
            AdaptationTarget.TEMPO_CAPACITY,
        ),
        interval_structure="threshold",
        min_duration=60,
        max_duration=120,
        aerobic_stress=StressLevel.HIGH,
        muscular_stress=StressLevel.MEDIUM,
        metabolic_stress=StressLevel.HIGH,
        neurological_stress=StressLevel.LOW,
    )


def threshold_4x8() -> TrainingRecipe:

    return build_recipe(
        id="threshold_4x8",
        name="Threshold 4x8",
        workout_type=WorkoutType.THRESHOLD,
        duration=90,
        target_tss=80,
        primary_system=EnergySystem.THRESHOLD,
        adaptations=(
            AdaptationTarget.FTP,
            AdaptationTarget.TEMPO_CAPACITY,
        ),
        interval_structure="4x8",
        min_duration=75,
        max_duration=120,
        aerobic_stress=StressLevel.HIGH,
        muscular_stress=StressLevel.MEDIUM,
        metabolic_stress=StressLevel.HIGH,
        neurological_stress=StressLevel.MEDIUM,
    )


def vo2_60() -> TrainingRecipe:

    return build_recipe(
        id="vo2_60",
        name="VO2 60",
        workout_type=WorkoutType.VO2,
        duration=60,
        target_tss=80,
        primary_system=EnergySystem.VO2MAX,
        adaptations=(
            AdaptationTarget.VO2MAX,
            AdaptationTarget.REPEATABILITY,
        ),
        interval_structure="5x5",
        min_duration=60,
        max_duration=90,
        aerobic_stress=StressLevel.HIGH,
        muscular_stress=StressLevel.MEDIUM,
        metabolic_stress=StressLevel.HIGH,
        neurological_stress=StressLevel.HIGH,
    )


def vo2_gorby() -> TrainingRecipe:

    return build_recipe(
        id="vo2_gorby",
        name="VO2 Gorby",
        workout_type=WorkoutType.VO2,
        duration=75,
        target_tss=85,
        primary_system=EnergySystem.VO2MAX,
        adaptations=(
            AdaptationTarget.VO2MAX,
            AdaptationTarget.REPEATABILITY,
        ),
        interval_structure="5x5_gorby",
        min_duration=60,
        max_duration=120,
        aerobic_stress=StressLevel.HIGH,
        muscular_stress=StressLevel.MEDIUM,
        metabolic_stress=StressLevel.HIGH,
        neurological_stress=StressLevel.HIGH,
    )