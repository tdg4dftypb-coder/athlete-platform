from dataclasses import dataclass

from athlete.history.event import AthleteEvent


@dataclass
class AthleteHistory:

    events: list[AthleteEvent]

    @property
    def count(self) -> int:

        return len(self.events)