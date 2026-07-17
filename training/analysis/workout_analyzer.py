from training.calculations.intensity_factor import IntensityFactor
from training.metrics import TrainingMetrics
from training.calculations.normalized_power import NormalizedPower
from training.calculations.power_zones import PowerZoneCalculator
from training.calculations.tss import TSS
from training.analysis.workout_summary import WorkoutSummary


class WorkoutAnalyzer:

    @staticmethod
    def efficiency_factor(activity):

        avg_hr = TrainingMetrics.average_hr(activity)

        if not avg_hr:
            return None

        np = NormalizedPower.calculate(activity)

        return np / avg_hr

    @staticmethod
    def variability_index(activity):

        avg_power = TrainingMetrics.average_power(activity)

        if not avg_power:
            return None

        np = NormalizedPower.calculate(activity)

        return np / avg_power

    @staticmethod
    def average_speed(activity):

        duration = TrainingMetrics.duration(activity)

        if not duration:
            return None

        hours = duration / 3600

        if hours == 0:
            return None

        return activity.distance / hours

    @staticmethod
    def average_pace(activity):

        speed = WorkoutAnalyzer.average_speed(activity)

        if not speed:
            return None

        return 60 / speed

    def analyze(self, activity):

        np = NormalizedPower.calculate(activity)

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

            normalized_power=np,

            max_power=TrainingMetrics.max_power(activity),

            intensity_factor=IntensityFactor.calculate(activity),

            tss=TSS.calculate(activity),

            efficiency_factor=self.efficiency_factor(activity),

            variability_index=self.variability_index(activity),

            average_speed=self.average_speed(activity),

            average_pace=self.average_pace(activity),

            hr_drift=None,

            aerobic_decoupling=None,

            training_load_ratio=None,

            elevation_gain=None,

            elevation_loss=None,

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