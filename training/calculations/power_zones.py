from dataclasses import dataclass

from training.ftp import FTP
from training.activity import Activity


@dataclass
class PowerZones:

    z1: int = 0
    z2: int = 0
    z3: int = 0
    z4: int = 0
    z5: int = 0
    z6: int = 0
    z7: int = 0


class PowerZoneCalculator:

    @staticmethod
    def calculate(activity: Activity) -> PowerZones:

        zones = PowerZones()

        for record in activity.records:

            if record.power is None:
                continue

            ratio = record.power / FTP

            if ratio < 0.55:
                zones.z1 += 1

            elif ratio < 0.75:
                zones.z2 += 1

            elif ratio < 0.90:
                zones.z3 += 1

            elif ratio < 1.05:
                zones.z4 += 1

            elif ratio < 1.20:
                zones.z5 += 1

            elif ratio < 1.50:
                zones.z6 += 1

            else:
                zones.z7 += 1

        return zones
