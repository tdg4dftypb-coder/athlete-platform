from athlete.history.builder import AthleteHistoryBuilder
from athlete.history.event import AthleteEvent
from athlete.history.models import AthleteHistory
from athlete.memory.models import AthleteMemoryEvent


class AthleteMemoryHistoryAdapter:

    def __init__(
        self,
        builder: AthleteHistoryBuilder | None = None,
    ) -> None:

        self.builder = builder or AthleteHistoryBuilder()

    def build(
        self,
        events: list[AthleteMemoryEvent],
    ) -> AthleteHistory:

        return self.builder.build(
            [
                AthleteEvent(
                    timestamp=event.occurred_at,
                    category=event.event_type.value,
                    title=event.payload["workout"]["name"],
                    payload=event.payload,
                )
                for event in events
            ]
        )
