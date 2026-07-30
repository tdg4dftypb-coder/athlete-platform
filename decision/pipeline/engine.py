from athlete.models import AthleteState

from decision.diagnosis import DiagnosisEngine
from decision.diagnosis.models import AthleteDiagnosis

from decision.prescription import PrescriptionEngine
from decision.prescription.models import TrainingPrescription


class DecisionPipeline:

    def __init__(self):

        self.diagnosis = DiagnosisEngine()
        self.prescription = PrescriptionEngine()

    def evaluate(
        self,
        athlete: AthleteState,
    ) -> tuple[
        AthleteDiagnosis,
        TrainingPrescription,
    ]:

        diagnosis = self.diagnosis.analyze(
            athlete,
        )

        prescription = self.prescription.prescribe(
            diagnosis,
        )

        return (
            diagnosis,
            prescription,
        )