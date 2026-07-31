from dataclasses import dataclass


@dataclass(frozen=True)
class SourceIdentity:
    """Identity of one source record within an external provider namespace."""

    provider: str
    external_id: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("SourceIdentity provider must not be empty")
        if not self.external_id.strip():
            raise ValueError("SourceIdentity external_id must not be empty")
