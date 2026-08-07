"""FixedDecisionIdGenerator for injecting pre-reserved decision IDs."""
class FixedDecisionIdGenerator:
    """DecisionIdGenerator implementation returning a pre-reserved decision identifier string."""

    def __init__(self, fixed_id: str) -> None:
        if not isinstance(fixed_id, str) or not fixed_id.strip():
            raise ValueError("fixed_id must be a non-empty string")
        self._fixed_id = fixed_id

    def generate(self) -> str:
        return self._fixed_id
