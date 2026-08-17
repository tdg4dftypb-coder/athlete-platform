from training.ingestion.fit_file_source_identity import FitFileSourceIdentity
from training.ingestion.source_identity import SourceIdentity


class ZwiftFitSourceIdentity(FitFileSourceIdentity):
    PROVIDER = "zwift_fit"

    def create(self, path):
        generic = super().create(path)
        return SourceIdentity(self.PROVIDER, generic.external_id)
