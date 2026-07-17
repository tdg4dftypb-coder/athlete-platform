from athlete.history.models import AthleteHistory


class AthleteHistoryRepository:

    def load(self) -> AthleteHistory:

        #
        # Sprint 1
        #
        # Na razie zwracamy pustą historię.
        # W kolejnych sprintach będą tu dołączane:
        #
        # - Workouts
        # - Sleep
        # - Body
        # - Blood
        # - Donations
        # - Equipment
        # - Notes
        # - Races
        #

        return AthleteHistory(events=[])