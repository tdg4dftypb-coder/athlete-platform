from scripts import demo_scenarios


def test_main_prints_all_controlled_morning_coach_scenarios(capsys):
    demo_scenarios.main()

    output = capsys.readouterr().out

    assert "INSUFFICIENT_DATA" in output
    assert "Morning Coach status: insufficient_data" in output
    assert "Adaptation directive: insufficient_data" in output
    assert "Today's workout: Endurance" in output
    assert "Training data is unavailable." in output
    assert "WorkoutBuilder output: Endurance Ride" in output

    assert "REDUCE_LOAD" in output
    assert "Morning Coach status: caution" in output
    assert "Adaptation directive: reduce_load" in output
    assert "Today's workout: Recovery" in output
    assert "Recovery status requires reduced load." in output
    assert "WorkoutBuilder output: Recovery Ride" in output

    assert "MAINTAIN" in output
    assert "Morning Coach status: stable" in output
    assert "Adaptation directive: maintain" in output
    assert "Today's workout: Endurance" in output
    assert "Long-term adaptation maintains the current plan." in output
