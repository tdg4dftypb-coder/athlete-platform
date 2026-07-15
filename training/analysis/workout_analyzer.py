from training.calculations.intensity_factor import IntensityFactor
from training.metrics import TrainingMetrics
from training.calculations.normalized_power import NormalizedPower
from training.calculations.power_zones import PowerZoneCalculator
from training.calculations.tss import TSS
from training.analysis.workout_summary import WorkoutSummary


class WorkoutAnalyzer:

    def analyze(self, activity):

        return WorkoutSummary(

            #
            # Session
            #

            start=activity.start,

            end=activity.end,

            sport=activity.sport,

            #
            # Basic
            #

            duration=TrainingMetrics.duration(activity),

            distance=activity.distance,

            calories=activity.calories,

            #
            # Power
            #

            average_power=TrainingMetrics.average_power(activity),

            normalized_power=NormalizedPower.calculate(activity),

            max_power=TrainingMetrics.max_power(activity),

            intensity_factor=IntensityFactor.calculate(activity),

            tss=TSS.calculate(activity),

            #
            # Heart Rate
            #

            average_hr=TrainingMetrics.average_hr(activity),

            max_hr=TrainingMetrics.max_hr(activity),

            #
            # Cadence
            #

            average_cadence=TrainingMetrics.average_cadence(activity),

            max_cadence=TrainingMetrics.max_cadence(activity),

            #
            # Zones
            #

            zones=PowerZoneCalculator.calculate(activity),
        )