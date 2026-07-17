from health.models import HealthState


class HealthEngine:

    def analyze(
        self,
        context,
    ) -> HealthState:

        return HealthState(

            #
            # Jeszcze nieobsługiwane
            #

            weight=None,

            #
            # Trendy z ContextBuilder
            #

            hrv=context.hrv,

            resting_hr=context.resting_hr,

            sleep=context.sleep,

            #
            # Jeszcze nieobsługiwane
            #

            steps=None,

        )