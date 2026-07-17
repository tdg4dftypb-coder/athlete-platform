from briefing.models import MorningBriefing


class BriefingEngine:

    def build(

        self,

        recovery,

        performance,

        decision,

        workout,

    ) -> MorningBriefing:

        return MorningBriefing(

            recovery=recovery,

            performance=performance,

            today=decision,

            last_workout=workout,

        )