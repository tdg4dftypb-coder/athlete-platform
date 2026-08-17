from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


class ZwiftSourceUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ZwiftArtifactSnapshot:
    discovered: tuple[Path, ...]
    ready: tuple[Path, ...]
    unstable: tuple[Path, ...]


class ZwiftFitArtifactDiscovery:
    STABILITY_SECONDS = 60
    BOOTSTRAP_DAYS = 90
    MAX_ARTIFACTS = 500

    def __init__(self, source_directory: Path | None):
        self.source_directory = source_directory

    def discover(self, observed_at: datetime) -> ZwiftArtifactSnapshot:
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.source_directory is None or not self.source_directory.is_dir():
            raise ZwiftSourceUnavailable("Zwift FIT provider folder is unavailable")
        threshold = observed_at.astimezone(timezone.utc) - timedelta(days=self.BOOTSTRAP_DAYS)
        candidates = []
        for path in self.source_directory.iterdir():
            if not path.is_file() or path.suffix.lower() != ".fit" or path.name.startswith("."):
                continue
            stat = path.stat()
            if stat.st_size == 0 or datetime.fromtimestamp(stat.st_mtime, timezone.utc) < threshold:
                continue
            candidates.append((stat.st_mtime_ns, path.name, path, stat))
        candidates.sort(key=lambda item: (item[0], item[1]))
        candidates = candidates[-self.MAX_ARTIFACTS:]
        discovered, ready, unstable = [], [], []
        for _, _, path, stat in candidates:
            discovered.append(path)
            age = observed_at.timestamp() - stat.st_mtime
            (ready if age >= self.STABILITY_SECONDS else unstable).append(path)
        return ZwiftArtifactSnapshot(tuple(discovered), tuple(ready), tuple(unstable))
