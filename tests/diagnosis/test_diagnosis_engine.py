from decision.diagnosis.engine import DiagnosisEngine
from decision.diagnosis.models import Readiness, RiskLevel
from tests.helpers import build_athlete, build_performance


def test_diagnosis_peak_readiness():
    athlete = build_athlete(recovery_score=90, freshness=75)
    diagnosis = DiagnosisEngine().analyze(athlete)
    assert diagnosis.readiness == Readiness.PEAK
    assert diagnosis.training_capacity == Readiness.HIGH
    assert diagnosis.injury_risk == RiskLevel.LOW


def test_diagnosis_high_readiness():
    athlete = build_athlete(recovery_score=75, fatigue=30)
    diagnosis = DiagnosisEngine().analyze(athlete)
    assert diagnosis.readiness == Readiness.HIGH
    assert diagnosis.training_capacity == Readiness.HIGH
    assert diagnosis.injury_risk == RiskLevel.LOW


def test_diagnosis_moderate_readiness():
    athlete = build_athlete(recovery_score=60, fatigue=50)
    diagnosis = DiagnosisEngine().analyze(athlete)
    assert diagnosis.readiness == Readiness.MODERATE
    assert diagnosis.training_capacity == Readiness.MODERATE
    assert diagnosis.injury_risk == RiskLevel.MODERATE


def test_diagnosis_high_fatigue_override():
    athlete = build_athlete(recovery_score=90, fatigue=85, freshness=75)
    diagnosis = DiagnosisEngine().analyze(athlete)
    assert diagnosis.readiness == Readiness.LOW
    assert diagnosis.training_capacity == Readiness.LOW
    assert diagnosis.injury_risk == RiskLevel.HIGH
    assert "High fatigue" in diagnosis.reasons


def test_diagnosis_high_fitness_capacity():
    athlete = build_athlete(recovery_score=60, fatigue=50)
    athlete.performance = build_performance(fatigue=50, freshness=0)
    athlete.performance.fitness = 85
    diagnosis = DiagnosisEngine().analyze(athlete)
    assert diagnosis.training_capacity == Readiness.HIGH
    assert "High fitness" in diagnosis.reasons