from .matching import match_evidence
from .models import (MatchMethod, ReconciliationStatus, SourceReconciliationResult,
                     canonical_activity_id)


class CrossSourceActivityReconciler:
    def __init__(self, repository): self.repository = repository

    def reconcile(self, observations, *, reconciled_at):
        zwift = tuple(item for item in observations if item.provider == "zwift_fit")
        supplemental = tuple(item for item in observations if item.provider != "zwift_fit")
        canonical = [(canonical_activity_id(item.provider, item.external_id),
                      item.provider, item.external_id) for item in zwift]
        results = []
        for item in supplemental:
            existing = self.repository.alias_target(item.provider, item.external_id)
            if existing:
                results.append(SourceReconciliationResult(item.provider, item.external_id,
                    ReconciliationStatus.ALREADY_MATCHED, existing,
                    MatchMethod.DETERMINISTIC_CANDIDATE, "existing_alias"))
                continue
            matches = [(candidate, match_evidence(candidate, item)) for candidate in zwift]
            matches = [(candidate, evidence) for candidate, evidence in matches if evidence]
            if len(matches) == 1:
                candidate, (method, evidence) = matches[0]
                results.append(SourceReconciliationResult(item.provider, item.external_id,
                    ReconciliationStatus.MATCHED,
                    canonical_activity_id(candidate.provider, candidate.external_id), method, evidence))
            elif len(matches) > 1:
                results.append(SourceReconciliationResult(item.provider, item.external_id,
                    ReconciliationStatus.AMBIGUOUS, None, None, f"candidate_count={len(matches)}"))
            else:
                results.append(SourceReconciliationResult(item.provider, item.external_id,
                    ReconciliationStatus.UNMATCHED, None, None, "no_conservative_match"))
        self.repository.persist(canonical, results, reconciled_at)
        return tuple(results)
