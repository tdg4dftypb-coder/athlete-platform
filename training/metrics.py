from training.activity import Activity


class TrainingMetrics:

    @staticmethod
    def average_power(
        activity: Activity,
    ) -> float:

        values = [

            r.power

            for r in activity.records

            if r.power is not None

        ]

        return sum(values) / len(values) if values else 0


    @staticmethod
    def max_power(
        activity: Activity,
    ) -> int:

        values = [

            r.power

            for r in activity.records

            if r.power is not None

        ]

        return max(values) if values else 0


    @staticmethod
    def average_hr(
        activity: Activity,
    ) -> float:

        values = [

            r.heart_rate

            for r in activity.records

            if r.heart_rate is not None

        ]

        return sum(values) / len(values) if values else 0


    @staticmethod
    def max_hr(
        activity: Activity,
    ) -> int:

        values = [

            r.heart_rate

            for r in activity.records

            if r.heart_rate is not None

        ]

        return max(values) if values else 0


    @staticmethod
    def average_cadence(
        activity: Activity,
    ) -> float:

        values = [

            r.cadence

            for r in activity.records

            if r.cadence is not None

        ]

        return sum(values) / len(values) if values else 0


    @staticmethod
    def max_cadence(
        activity: Activity,
    ) -> int:

        values = [

            r.cadence

            for r in activity.records

            if r.cadence is not None

        ]

        return max(values) if values else 0


    @staticmethod
    def duration(
        activity: Activity,
    ) -> int:

        return activity.duration