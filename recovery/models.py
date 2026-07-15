from dataclasses import dataclass


@dataclass
class RecoveryResult:

    score: int

    status: str

    reasons: list[str]