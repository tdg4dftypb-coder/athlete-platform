from pipeline.models import PostWorkoutResult


class WorkoutCompletedSerializer:

    SCHEMA_VERSION = 1

    def serialize(
        self,
        result: PostWorkoutResult,
    ) -> dict:

        return {
            "schema_version": self.SCHEMA_VERSION,
            "workout": {
                "name": result.workout.name,
                "goal": str(result.workout.goal),
                "description": result.workout.description,
                "duration": result.workout.duration,
                "target_tss": result.workout.target_tss,
                "target_if": result.workout.target_if,
                "blocks": [
                    {
                        "name": block.name,
                        "description": block.description,
                        "duration": block.duration,
                        "power_from": block.power_from,
                        "power_to": block.power_to,
                        "cadence_from": block.cadence_from,
                        "cadence_to": block.cadence_to,
                        "repeat": block.repeat,
                    }
                    for block in result.workout.blocks
                ],
            },
            "activity": {
                "start": result.activity.start.isoformat(),
                "end": result.activity.end.isoformat(),
                "sport": result.activity.sport,
                "distance": result.activity.distance,
                "calories": result.activity.calories,
                "duration": result.activity.duration,
            },
            "workout_summary": {
                "average_power": result.workout_summary.average_power,
                "normalized_power": result.workout_summary.normalized_power,
                "max_power": result.workout_summary.max_power,
                "intensity_factor": result.workout_summary.intensity_factor,
                "tss": result.workout_summary.tss,
                "average_hr": result.workout_summary.average_hr,
                "max_hr": result.workout_summary.max_hr,
                "average_cadence": result.workout_summary.average_cadence,
                "max_cadence": result.workout_summary.max_cadence,
            },
            "execution": {
                "planned_duration": result.execution.planned_duration,
                "executed_duration": result.execution.executed_duration,
                "planned_tss": result.execution.planned_tss,
                "executed_tss": result.execution.executed_tss,
                "completion_score": result.execution.completion_score,
                "execution_score": result.execution.execution_score,
                "completed": result.execution.completed,
                "insights": list(result.execution.insights),
                "blocks": [
                    {
                        "name": block.name,
                        "planned_duration": block.planned_duration,
                        "executed_duration": block.executed_duration,
                        "completion_score": block.completion_score,
                        "power_score": block.power_score,
                        "cadence_score": block.cadence_score,
                        "heart_rate_score": block.heart_rate_score,
                        "execution_score": block.execution_score,
                        "deviations": list(block.deviations),
                    }
                    for block in result.execution.blocks
                ],
            },
            "feedback": {
                "status": result.feedback.status.value,
                "headline": result.feedback.headline,
                "summary": result.feedback.summary,
                "execution_score": result.feedback.execution_score,
                "completion_score": result.feedback.completion_score,
                "positive_signals": [
                    self._signal_payload(signal)
                    for signal in result.feedback.positive_signals
                ],
                "attention_signals": [
                    self._signal_payload(signal)
                    for signal in result.feedback.attention_signals
                ],
            },
        }

    @staticmethod
    def _signal_payload(signal) -> dict:

        return {
            "code": signal.code,
            "message": signal.message,
            "block_name": signal.block_name,
        }
