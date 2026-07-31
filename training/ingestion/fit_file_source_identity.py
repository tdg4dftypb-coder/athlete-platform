from hashlib import sha256
from pathlib import Path

from training.ingestion.source_identity import SourceIdentity


class FitFileSourceIdentity:
    """Creates artifact identities for FIT files without parsing FIT messages."""

    PROVIDER = "fit_file"
    CHUNK_SIZE = 64 * 1024

    def create(self, path: Path) -> SourceIdentity:
        digest = sha256()

        with path.open("rb") as file:
            while chunk := file.read(self.CHUNK_SIZE):
                digest.update(chunk)

        return SourceIdentity(
            provider=self.PROVIDER,
            external_id=f"sha256:{digest.hexdigest()}",
        )
