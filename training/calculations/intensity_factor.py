from training.ftp import FTP
from training.calculations.normalized_power import NormalizedPower
from training.raw_activity import RawActivity


class IntensityFactor:

    @staticmethod
    def calculate(activity: RawActivity) -> float:

        if FTP == 0:
            return 0

        np = NormalizedPower.calculate(activity)

        return np / FTP