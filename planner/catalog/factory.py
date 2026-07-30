from planner.catalog.analytics import AnalyticsProfile
from planner.catalog.aggregate import TrainingRecipe
from planner.catalog.identity import TrainingIdentity
from planner.catalog.prescription import WorkoutPrescription
from planner.catalog.selection import SelectionProfile
from planner.catalog.stimulus import (
    EnergySystem,
    StressLevel,
    TrainingStimulus,
)

from planner.catalog.models import (
    CadenceType,
    FuelStrategy,
    LoadLevel,
    RideProfile,
    TerrainType,
    WorkoutTag,
)

from workout.enums import WorkoutType


class RecipeFactory:

    @staticmethod
    def create(
        *,
        id: str,
        name: str,
        dsl: WorkoutType,
        workout_type: WorkoutType,
        duration: int,
        target_tss: int,
        priority: int,
        tags: tuple[WorkoutTag, ...],
        terrain: tuple[TerrainType, ...],
        cadence: CadenceType,
        fuel_strategy: FuelStrategy,
        ride_profile: RideProfile,
        aerobic_load: LoadLevel,
        muscular_load: LoadLevel,
        neurological_load: LoadLevel,
    ) -> TrainingRecipe:

        return TrainingRecipe(
            identity=TrainingIdentity(
                id=id,
                name=name,
                workout_type=workout_type,
                dsl=dsl,
            ),

            stimulus=TrainingStimulus(
                primary_system=(
                    EnergySystem.RECOVERY
                    if workout_type == WorkoutType.RECOVERY
                    else EnergySystem.AEROBIC
                ),
                aerobic_stress=StressLevel[aerobic_load.name],
                muscular_stress=StressLevel[muscular_load.name],
                metabolic_stress=StressLevel.MEDIUM,
                neurological_stress=StressLevel[neurological_load.name],
            ),

            prescription=WorkoutPrescription(
                duration=duration,
                target_tss=target_tss,
                interval_structure="factory_generated",
            ),

            selection=SelectionProfile(
                min_duration=duration,
                max_duration=duration,
            ),

            analytics=AnalyticsProfile(
                aerobic_load=StressLevel[aerobic_load.name],
                muscular_load=StressLevel[muscular_load.name],
                metabolic_load=StressLevel.MEDIUM,
                neurological_load=StressLevel[neurological_load.name],
                fatigue_index=target_tss / 100,
            ),
        )