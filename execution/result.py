from dataclasses import dataclass, field


@dataclass(frozen=True)
class BlockExecutionResult:

    name: str

    planned_duration: int

    executed_duration: int

    completion_score: float

    power_score: float | None

    cadence_score: float | None

    heart_rate_score: float | None

    execution_score: float

    deviations: list[str] = field(
        default_factory=list,
    )


@dataclass(frozen=True)
class ExecutionResult:
    """Technical result whose completion and execution scores are 0-100 percentages.

    A value of 0.90 means 0.90%, not 90%.
    """

    planned_duration: int

    executed_duration: int

    planned_tss: float

    executed_tss: float

    completion_score: float

    power_score: float | None

    cadence_score: float | None

    heart_rate_score: float | None

    execution_score: float

    completed: bool

    blocks: list[BlockExecutionResult] = field(
        default_factory=list,
    )

    insights: list[str] = field(
        default_factory=list,
    )
