from types import SimpleNamespace
from unittest.mock import Mock

from scripts import morning_coach
from schema.athlete_memory_schema import AthleteMemorySchema


def test_main_runs_the_cli_and_prints_the_morning_coach_report(
    monkeypatch,
    capsys,
):
    report = SimpleNamespace(
        athlete_assessment=SimpleNamespace(
            status=SimpleNamespace(value="stable"),
        ),
        workout=SimpleNamespace(name="Endurance"),
        explanation=SimpleNamespace(
            summary="Today's recommendation: Endurance ride.",
            reasons=(
                "Long-term adaptation maintains the current plan.",
                "Endurance workout has been selected.",
            ),
        ),
    )
    monkeypatch.setattr(morning_coach, "build_report", lambda: report)

    morning_coach.main()

    assert capsys.readouterr().out == (
        "=========================================\n"
        "AI COACH\n"
        "=========================================\n"
        "\n"
        "Status:\n"
        "stable\n"
        "\n"
        "Today's workout:\n"
        "Endurance\n"
        "\n"
        "Explanation:\n"
        "Today's recommendation: Endurance ride.\n"
        "\n"
        "Reasons:\n"
        "- Long-term adaptation maintains the current plan.\n"
        "- Endurance workout has been selected.\n"
        "\n"
        "=========================================\n"
    )


def test_build_report_does_not_create_the_athlete_memory_schema(monkeypatch):
    report = SimpleNamespace()
    created_schema = Mock()
    database = Mock()

    class FakeUseCase:
        def __init__(self, **_dependencies):
            pass

        def run(self):
            return SimpleNamespace(report=report)

    monkeypatch.setattr(morning_coach, "Database", lambda: database)
    monkeypatch.setattr(morning_coach, "HealthRepository", Mock())
    monkeypatch.setattr(morning_coach, "MorningCoachUseCase", FakeUseCase)
    monkeypatch.setattr(AthleteMemorySchema, "create", created_schema)

    assert morning_coach.build_report() is report
    created_schema.assert_not_called()
    database.close.assert_called_once_with()
