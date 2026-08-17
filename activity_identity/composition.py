"""Failure-isolated, inactive source-sync composition for the DIG.5 operator gates."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRunState:
    provider: str
    status: str
    error_code: str | None = None


class DataSourceSyncCoordinator:
    def __init__(self, providers): self.providers = providers

    def run(self):
        states = []
        for name, service in self.providers.items():
            if service is None:
                states.append(ProviderRunState(name, "DISABLED"))
                continue
            try:
                service()
                states.append(ProviderRunState(name, "READY"))
            except Exception as error:
                states.append(ProviderRunState(name, "DEGRADED", type(error).__name__))
        return tuple(states)
