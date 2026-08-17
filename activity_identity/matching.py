from .models import MatchMethod

START_TOLERANCE_SECONDS = 120
DURATION_TOLERANCE_RATIO = 0.05
DURATION_TOLERANCE_FLOOR_SECONDS = 60


def compatible_sport(left: str, right: str) -> bool:
    aliases = {"ride": "cycling", "virtualride": "cycling", "bike": "cycling",
               "run": "running", "virtualrun": "running", "swim": "swimming"}
    normalize = lambda value: aliases.get(value.replace("_", "").replace(" ", "").lower(), value.lower())
    return normalize(left) == normalize(right)


def match_evidence(canonical, supplemental):
    if (supplemental.linked_provider == canonical.provider and
            supplemental.linked_external_id == canonical.external_id):
        return MatchMethod.EXACT_LINK, "explicit_provider_link"
    if not compatible_sport(canonical.sport, supplemental.sport):
        return None
    start_delta = abs((canonical.start_at - supplemental.start_at).total_seconds())
    if start_delta > START_TOLERANCE_SECONDS:
        return None
    duration_delta = abs(canonical.duration_seconds - supplemental.duration_seconds)
    allowed = max(DURATION_TOLERANCE_FLOOR_SECONDS,
                  canonical.duration_seconds * DURATION_TOLERANCE_RATIO)
    if duration_delta > allowed:
        return None
    evidence = f"sport;start_delta={int(start_delta)}s;duration_delta={int(duration_delta)}s"
    if canonical.distance_meters is not None and supplemental.distance_meters is not None:
        evidence += f";distance_delta={int(abs(canonical.distance_meters-supplemental.distance_meters))}m"
    return MatchMethod.DETERMINISTIC_CANDIDATE, evidence
