from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.composition import build_morning_coach_use_case
from core.database import Database
from dashboard.serialization import DashboardSerializer


def main() -> None:
    target_dir = ROOT / "web" / "AthleteWeb" / "public" / "data"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "athlete-dashboard-v1.json"

    database = Database()
    try:
        use_case = build_morning_coach_use_case(database)
        result = use_case.run()
        if result.dashboard is None:
            raise RuntimeError("Failed to build AthleteDashboard instance from backend engine")

        payload = DashboardSerializer().serialize(result.dashboard)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"Exported AthleteDashboard v1.0 payload to {target_file}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
