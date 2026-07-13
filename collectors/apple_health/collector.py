import json

from datetime import date

from core.models import HealthDaily


class AppleHealthCollector:

    def load_today(self, filepath: str) -> HealthDaily:

        with open(filepath, "r") as f:
            data = json.load(f)

        return HealthDaily(
            date=date.fromisoformat(data["date"]),
            weight=data.get("weight"),
            sleep_duration=data.get("sleep_duration"),
            sleep_score=data.get("sleep_score"),
            hrv=data.get("hrv"),
            resting_hr=data.get("resting_hr"),
            active_energy=data.get("active_energy"),
            resting_energy=data.get("resting_energy"),
            steps=data.get("steps"),
            respiratory_rate=data.get("respiratory_rate"),
            spo2=data.get("spo2"),
            wrist_temperature=data.get("wrist_temperature"),
        )