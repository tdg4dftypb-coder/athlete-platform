from workout.models import Workout


class WorkoutValidator:

    def validate(
        self,
        workout: Workout,
    ) -> list[str]:

        errors = []

        if workout.duration <= 0:

            errors.append(
                "Workout duration must be greater than zero."
            )

        if len(workout.blocks) == 0:

            errors.append(
                "Workout contains no blocks."
            )

        total = sum(
            block.duration * block.repeat
            for block in workout.blocks
        )

        if total != workout.duration * 60:

            errors.append(
                "Workout duration does not match block duration."
            )

        for block in workout.blocks:

            if block.power_from > block.power_to:

                errors.append(
                    f"{block.name}: invalid power range."
                )

            if block.cadence_from > block.cadence_to:

                errors.append(
                    f"{block.name}: invalid cadence range."
                )

        return errors