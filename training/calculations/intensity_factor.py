from training.ftp import FTP
from training.calculations.normalized_power import NormalizedPower
from training.activity import Activity


class IntensityFactor:

    @staticmethod
    def calculate(activity: Activity) -> float:

        if FTP == 0:
            return 0

        np = NormalizedPower.calculate(activity)

        return np / FTP
