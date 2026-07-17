from athlete.history.event import AthleteEvent
from athlete.history.models import AthleteHistory


class AthleteHistoryBuilder:

    def build(
        self,
        events: list[AthleteEvent],
    ) -> AthleteHistory:

        events = sorted(

            events,

            key=lambda x: x.timestamp,

            reverse=True,

        )

        return AthleteHistory(events)