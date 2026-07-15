from training.raw_activity import RawActivity


class TrainingMetrics:

    @staticmethod
    def average_power(activity: RawActivity) -> float:

        values = [
            r.power
            for r in activity.records
            if r.power is not None
        ]

        return sum(values) / len(values) if values else 0

    @staticmethod
    def max_power(activity: RawActivity) -> int:

        values = [
            r.power
            for r in activity.records
            if r.power is not None
        ]

        return max(values) if values else 0

    @staticmethod
    def average_hr(activity: RawActivity) -> float:

        values = [
            r.heart_rate
            for r in activity.records
            if r.heart_rate is not None
        ]

        return sum(values) / len(values) if values else 0

    @staticmethod
    def max_hr(activity: RawActivity) -> int:

        values = [
            r.heart_rate
            for r in activity.records
            if r.heart_rate is not None
        ]

        return max(values) if values else 0

    @staticmethod
    def average_cadence(activity: RawActivity) -> float:

        values = [
            r.cadence
            for r in activity.records
            if r.cadence is not None
        ]

        return sum(values) / len(values) if values else 0

    @staticmethod
    def max_cadence(activity: RawActivity) -> int:

        values = [
            r.cadence
            for r in activity.records
            if r.cadence is not None
        ]

        return max(values) if values else 0

    @staticmethod
    def duration(activity: RawActivity) -> int:

        return len(activity.records)