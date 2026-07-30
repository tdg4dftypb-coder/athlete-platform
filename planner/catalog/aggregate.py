from dataclasses import dataclass

from planner.catalog.analytics import AnalyticsProfile
from planner.catalog.identity import TrainingIdentity
from planner.catalog.prescription import WorkoutPrescription
from planner.catalog.selection import SelectionProfile
from planner.catalog.stimulus import TrainingStimulus


@dataclass(frozen=True, slots=True)
class TrainingRecipe:

    identity: TrainingIdentity

    stimulus: TrainingStimulus

    prescription: WorkoutPrescription

    selection: SelectionProfile

    analytics: AnalyticsProfile


    @property
    def id(
        self,
    ) -> str:

        return self.identity.id