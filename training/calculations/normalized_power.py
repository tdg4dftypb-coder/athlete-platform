from training.raw_activity import RawActivity


class NormalizedPower:

    @staticmethod
    def calculate(activity: RawActivity) -> float:

        power = [
            r.power if r.power is not None else 0
            for r in activity.records
        ]

        if len(power) < 30:
            return 0

        #
        # 30-second rolling average
        #

        rolling = []

        for i in range(29, len(power)):

            avg = sum(power[i - 29:i + 1]) / 30

            rolling.append(avg)

        #
        # Fourth power
        #

        fourth = [p ** 4 for p in rolling]

        mean = sum(fourth) / len(fourth)

        return mean ** 0.25