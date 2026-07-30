from training.ftp import FTP
from training.calculations.intensity_factor import IntensityFactor
from training.calculations.normalized_power import NormalizedPower
from training.activity import Activity


class TSS:

    @staticmethod
    def calculate(
        activity: Activity,
    ) -> float:

        if FTP == 0:

            return 0


        duration = activity.duration


        np = NormalizedPower.calculate(

            activity,

        )


        intensity = IntensityFactor.calculate(

            activity,

        )


        tss = (

            duration

            *

            np

            *

            intensity

        ) / (FTP * 3600) * 100


        return round(

            tss,

            1,

        )