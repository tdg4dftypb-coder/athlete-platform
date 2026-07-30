from simulator.models import (
    SimulatedBlock,
    SimulatedWorkout,
)

from workout.models import Workout


class SimulatorEngine:

    FTP = 285.0

    def simulate(
        self,
        workout: Workout,
    ) -> SimulatedWorkout:

        blocks = []

        total_seconds = 0
        weighted_power = 0.0
        total_tss = 0.0

        for block in workout.blocks:

            power = (
                block.power_from +
                block.power_to
            ) / 2

            watts = power * self.FTP

            duration_hours = block.duration / 3600

            intensity = power

            tss = (
                duration_hours *
                intensity *
                intensity *
                100
            )

            blocks.append(
                SimulatedBlock(
                    name=block.name,
                    duration=block.duration,
                    average_power=watts,
                    normalized_power=watts,
                    intensity_factor=intensity,
                    tss=tss,
                )
            )

            total_seconds += block.duration

            weighted_power += watts * block.duration

            total_tss += tss

        if workout.target_tss > 0 and total_tss > 0:

            scale = (
                workout.target_tss /
                total_tss
            )

            total_tss = workout.target_tss

            for block in blocks:
                block.tss *= scale

        average_power = (
            weighted_power / total_seconds
            if total_seconds
            else 0
        )

        return SimulatedWorkout(
            duration=total_seconds,
            average_power=average_power,
            normalized_power=average_power,
            intensity_factor=average_power / self.FTP,
            tss=total_tss,
            blocks=blocks,
        )