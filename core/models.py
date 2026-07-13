from dataclasses import dataclass
from datetime import date
from typing import Optional


# ======================================================
# Daily Health
# ======================================================

@dataclass
class HealthDaily:
    date: date

    weight: Optional[float] = None

    sleep_duration: Optional[int] = None
    sleep_score: Optional[int] = None

    hrv: Optional[int] = None
    resting_hr: Optional[int] = None

    active_energy: Optional[int] = None
    resting_energy: Optional[int] = None

    steps: Optional[int] = None

    respiratory_rate: Optional[float] = None
    spo2: Optional[float] = None
    wrist_temperature: Optional[float] = None


# ======================================================
# Daily Training
# ======================================================

@dataclass
class TrainingDaily:
    date: date

    duration: Optional[int] = None

    load: Optional[int] = None
    tss: Optional[int] = None

    kj: Optional[int] = None
    kcal: Optional[int] = None

    ftp: Optional[int] = None

    intensity_factor: Optional[float] = None
    np: Optional[int] = None

    workout_name: Optional[str] = None


# ======================================================
# Body Composition
# ======================================================

@dataclass
class BodyComposition:
    date: date

    weight: Optional[float] = None

    body_fat: Optional[float] = None

    muscle_mass: Optional[float] = None

    visceral_fat: Optional[float] = None

    body_water: Optional[float] = None

    bmr: Optional[int] = None

    waist: Optional[float] = None


# ======================================================
# Blood Tests
# ======================================================

@dataclass
class BloodTest:
    date: date

    ferritin: Optional[float] = None
    iron: Optional[float] = None

    vitamin_b12: Optional[float] = None
    vitamin_d: Optional[float] = None

    glucose: Optional[float] = None
    hba1c: Optional[float] = None

    tsh: Optional[float] = None

    alt: Optional[float] = None
    ast: Optional[float] = None

    creatinine: Optional[float] = None


# ======================================================
# Blood Donation
# ======================================================

@dataclass
class BloodDonation:
    date: date

    donation_type: str = "whole_blood"

    volume_ml: Optional[int] = 450