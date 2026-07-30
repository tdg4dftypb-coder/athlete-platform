from types import SimpleNamespace

from scripts import morning_coach


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
