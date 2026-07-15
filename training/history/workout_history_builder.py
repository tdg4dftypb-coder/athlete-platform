from repositories.workout_repository import WorkoutRepository

from training.calculations.power_zones import PowerZones
from training.analysis.workout_summary import WorkoutSummary
from training.history.workout_history import WorkoutHistory


class WorkoutHistoryBuilder:

    def __init__(self):

        self.repository = WorkoutRepository()

    def last_days(
        self,
        days: int,
    ) -> WorkoutHistory:

        rows = self.repository.last_days(days)

        workouts = []

        for row in rows:

            workouts.append(

                WorkoutSummary(

                    #
                    # Session
                    #

                    start=row[1],

                    end=row[2],

                    sport=row[3],

                    #
                    # Basic
                    #

                    duration=row[4],

                    distance=row[5],

                    calories=row[6],

                    #
                    # Power
                    #

                    average_power=row[7],

                    normalized_power=row[8],

                    max_power=row[9],

                    intensity_factor=row[10],

                    tss=row[11],

                    #
                    # HR
                    #

                    average_hr=row[12],

                    max_hr=row[13],

                    #
                    # Cadence
                    #

                    average_cadence=row[14],

                    max_cadence=row[15],

                    #
                    # Zones
                    #

                    zones=PowerZones(

                        z1=row[16],
                        z2=row[17],
                        z3=row[18],
                        z4=row[19],
                        z5=row[20],
                        z6=row[21],
                        z7=row[22],

                    ),

                )

            )

        return WorkoutHistory(workouts)