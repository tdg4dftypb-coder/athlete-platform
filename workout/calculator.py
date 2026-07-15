from training.ftp import FTP

from workout.metrics import WorkoutMetrics
from workout.models import Workout


class WorkoutCalculator:

    def calculate(
        self,
        workout: Workout,
    ) -> WorkoutMetrics:

        seconds = 0

        weighted_power = 0

        z1 = z2 = z3 = z4 = z5 = z6 = z7 = 0

        for block in workout.blocks:

            duration = block.duration * block.repeat

            power = (
                block.power_from +
                block.power_to
            ) / 2

            seconds += duration

            weighted_power += power * duration

            if power < 0.55:

                z1 += duration

            elif power < 0.75:

                z2 += duration

            elif power < 0.90:

                z3 += duration

            elif power < 1.05:

                z4 += duration

            elif power < 1.20:

                z5 += duration

            elif power < 1.50:

                z6 += duration

            else:

                z7 += duration

        avg_if = weighted_power / seconds

        np = avg_if * FTP

        tss = (
            workout.duration
            * avg_if
            * avg_if
            * 100
            / 60
        )

        calories = int(
            np * workout.duration * 60 / 1000 * 3.6
        )

        return WorkoutMetrics(

            duration=workout.duration,

            expected_if=avg_if,

            expected_np=np,

            expected_tss=tss,

            estimated_calories=calories,

            z1=z1,

            z2=z2,

            z3=z3,

            z4=z4,

            z5=z5,

            z6=z6,

            z7=z7,
        )