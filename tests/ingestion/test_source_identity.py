from dataclasses import FrozenInstanceError

import pytest

from training.ingestion import SourceIdentity


def test_source_identity_keeps_provider_and_external_id():
    identity = SourceIdentity(
        provider="fit_file",
        external_id="sha256:abc",
    )

    assert identity.provider == "fit_file"
    assert identity.external_id == "sha256:abc"


def test_source_identity_is_immutable():
    identity = SourceIdentity(provider="fit_file", external_id="sha256:abc")

    with pytest.raises(FrozenInstanceError):
        identity.provider = "garmin_connect"


@pytest.mark.parametrize("provider", ("", "   "))
def test_source_identity_rejects_empty_provider(provider):
    with pytest.raises(ValueError, match="provider"):
        SourceIdentity(provider=provider, external_id="external-id")


@pytest.mark.parametrize("external_id", ("", "   "))
def test_source_identity_rejects_empty_external_id(external_id):
    with pytest.raises(ValueError, match="external_id"):
        SourceIdentity(provider="fit_file", external_id=external_id)


def test_external_id_is_interpreted_in_the_provider_namespace():
    external_id = "record-123"

    assert SourceIdentity("fit_file", external_id) != SourceIdentity(
        "garmin_connect",
        external_id,
    )
