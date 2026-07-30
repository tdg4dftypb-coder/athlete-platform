from athlete.memory.models import (
    AthleteMemorySnapshot,
    PatternReport,
    TrainingPattern,
    WorkoutMemoryObservation,
)


class PatternDetector:
    """Detects patterns from percentage scores; TSS thresholds use load ratios."""

    CONSISTENT_EXECUTION_MIN_SCORE = 90.0
    PARTIAL_EXECUTION_MAX_SCORE = 80.0

    def analyze(
        self,
        snapshot: AthleteMemorySnapshot,
    ) -> PatternReport:

        observations = snapshot.workout_observations
        patterns = (
            self._consistent_execution(observations),
            self._repeated_partial_execution(observations),
            self._repeated_under_execution(observations),
            self._repeated_over_execution(observations),
        )

        return PatternReport(
            period=snapshot.period,
            patterns=tuple(pattern for pattern in patterns if pattern is not None),
            source_event_ids=snapshot.source_event_ids,
        )

    @staticmethod
    def _consistent_execution(
        observations: tuple[WorkoutMemoryObservation, ...],
    ) -> TrainingPattern | None:

        if len(observations) < 3:
            return None
        if not all(
            observation.completion_score >= PatternDetector.CONSISTENT_EXECUTION_MIN_SCORE
            and observation.execution_score >= PatternDetector.CONSISTENT_EXECUTION_MIN_SCORE
            for observation in observations
        ):
            return None

        return TrainingPattern(
            code="CONSISTENT_EXECUTION",
            severity="INFO",
            description="All workouts in the period were executed consistently.",
            source_event_ids=tuple(
                observation.event_id
                for observation in observations
            ),
        )

    @staticmethod
    def _repeated_partial_execution(
        observations: tuple[WorkoutMemoryObservation, ...],
    ) -> TrainingPattern | None:

        matching = tuple(
            observation
            for observation in observations
            if 0 < observation.completion_score < PatternDetector.PARTIAL_EXECUTION_MAX_SCORE
        )
        if len(matching) < 2:
            return None

        return TrainingPattern(
            code="REPEATED_PARTIAL_EXECUTION",
            severity="WARNING",
            description="Multiple workouts were only partially completed.",
            source_event_ids=tuple(
                observation.event_id
                for observation in matching
            ),
        )

    @staticmethod
    def _repeated_under_execution(
        observations: tuple[WorkoutMemoryObservation, ...],
    ) -> TrainingPattern | None:

        matching = tuple(
            observation
            for observation in observations
            if observation.planned_tss > 0
            and observation.executed_tss / observation.planned_tss < 0.85
        )
        if len(matching) < 2:
            return None

        return TrainingPattern(
            code="REPEATED_UNDER_EXECUTION",
            severity="WARNING",
            description="Multiple workouts were executed below planned load.",
            source_event_ids=tuple(
                observation.event_id
                for observation in matching
            ),
        )

    @staticmethod
    def _repeated_over_execution(
        observations: tuple[WorkoutMemoryObservation, ...],
    ) -> TrainingPattern | None:

        matching = tuple(
            observation
            for observation in observations
            if observation.planned_tss > 0
            and observation.executed_tss / observation.planned_tss > 1.15
        )
        if len(matching) < 2:
            return None

        return TrainingPattern(
            code="REPEATED_OVER_EXECUTION",
            severity="WARNING",
            description="Multiple workouts were executed above planned load.",
            source_event_ids=tuple(
                observation.event_id
                for observation in matching
            ),
        )
