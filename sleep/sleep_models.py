from dataclasses import dataclass


@dataclass
class SleepSummary:

    duration: int = 0

    in_bed: int = 0

    awake: int = 0

    rem: int = 0

    core: int = 0

    deep: int = 0

    unspecified: int = 0

    @property
    def efficiency(self):

        if self.in_bed == 0:
            return None

        return (self.duration / self.in_bed) * 100