from hashlib import sha256
from pathlib import Path

from training.ingestion.fit_file_source_identity import FitFileSourceIdentity


def test_fit_file_identity_uses_sha256_of_all_raw_bytes(tmp_path):
    payload = b"FIT artifact\x00\xff"
    path = tmp_path / "activity.fit"
    path.write_bytes(payload)

    identity = FitFileSourceIdentity().create(path)

    assert identity.provider == "fit_file"
    assert identity.external_id == f"sha256:{sha256(payload).hexdigest()}"


def test_identical_bytes_under_different_names_have_the_same_identity(tmp_path):
    payload = b"same FIT artifact"
    original = tmp_path / "original.fit"
    copy = tmp_path / "renamed-copy.fit"
    original.write_bytes(payload)
    copy.write_bytes(payload)

    creator = FitFileSourceIdentity()

    assert creator.create(original) == creator.create(copy)


def test_different_bytes_have_different_identities(tmp_path):
    first = tmp_path / "first.fit"
    second = tmp_path / "second.fit"
    first.write_bytes(b"first artifact")
    second.write_bytes(b"second artifact")

    creator = FitFileSourceIdentity()

    assert creator.create(first) != creator.create(second)


def test_empty_file_has_a_deterministic_identity(tmp_path):
    path = tmp_path / "empty.fit"
    path.write_bytes(b"")

    identity = FitFileSourceIdentity().create(path)

    assert identity.external_id == f"sha256:{sha256(b'').hexdigest()}"


def test_identity_reads_the_file_in_fixed_size_chunks(tmp_path, monkeypatch):
    path = tmp_path / "large.fit"
    path.write_bytes(b"x" * (FitFileSourceIdentity.CHUNK_SIZE * 2 + 1))
    read_sizes = []
    original_open = Path.open

    class TrackingFile:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def read(self, size=-1):
            read_sizes.append(size)
            return self.file.read(size)

    def tracking_open(file_path, *args, **kwargs):
        return TrackingFile(original_open(file_path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", tracking_open)

    FitFileSourceIdentity().create(path)

    assert len(read_sizes) > 1
    assert set(read_sizes) == {FitFileSourceIdentity.CHUNK_SIZE}
