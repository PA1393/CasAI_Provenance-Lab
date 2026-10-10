from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.rights.service import is_commercially_eligible
from app.schemas.contracts import (
    ApprovalRecord,
    ApprovalScope,
    ArtifactRecord,
    PermissionBasis,
    RightsGrant,
    RightsScope,
    RightsStatus,
    SourceKind,
    SourceRecord,
    Visibility,
)

NOW = datetime(2026, 10, 9, tzinfo=UTC)
SHA256 = "a" * 64


def _grant(**overrides) -> RightsGrant:
    values = {
        "rights_grant_id": uuid4(),
        "source_version_id": uuid4(),
        "scope": RightsScope.COMMERCIAL_LICENSE,
        "status": RightsStatus.ACTIVE,
        "permission_basis": PermissionBasis.EXPLICIT_CONSENT,
        "explicit_permission": True,
        "granted_by": "customer:123",
        "effective_at": NOW - timedelta(days=1),
        "created_at": NOW - timedelta(days=1),
    }
    values.update(overrides)
    return RightsGrant(**values)


def test_customer_source_is_private_by_default() -> None:
    source = SourceRecord(
        source_id=uuid4(),
        source_version_id=uuid4(),
        version=1,
        source_kind=SourceKind.CUSTOMER_UPLOAD,
        owner_ref="customer:123",
        sha256=SHA256,
        created_at=NOW,
    )

    assert source.visibility == Visibility.PRIVATE
    assert source.schema_version == 1


def test_artifact_is_private_and_versioned_by_default() -> None:
    artifact = ArtifactRecord(
        artifact_id=uuid4(),
        artifact_version_id=uuid4(),
        version=1,
        artifact_type="validated_input_package",
        owner_ref="customer:123",
        sha256=SHA256,
        byte_size=128,
        media_type="application/json",
        storage_uri="supabase://artifacts/example.json",
        created_at=NOW,
    )

    assert artifact.visibility == Visibility.PRIVATE
    assert artifact.version == 1


def test_rights_grant_requires_exactly_one_versioned_target() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        _grant(source_version_id=None)

    with pytest.raises(ValidationError, match="exactly one"):
        _grant(artifact_version_id=uuid4())


def test_approval_requires_exactly_one_versioned_target() -> None:
    values = {
        "approval_id": uuid4(),
        "scope": ApprovalScope.PLAN,
        "requested_by": "user:reviewer",
        "created_at": NOW,
    }
    with pytest.raises(ValidationError, match="exactly one"):
        ApprovalRecord(**values)

    approval = ApprovalRecord(**values, run_id=uuid4())
    assert approval.run_id is not None


def test_private_customer_record_is_not_commercially_eligible_without_grant() -> None:
    assert is_commercially_eligible([], at=NOW) is False


@pytest.mark.parametrize(
    "grant",
    [
        _grant(explicit_permission=False),
        _grant(scope=RightsScope.RESEARCH_USE),
        _grant(status=RightsStatus.REVOKED, revoked_at=NOW - timedelta(hours=1)),
        _grant(expires_at=NOW - timedelta(seconds=1)),
        _grant(effective_at=NOW + timedelta(seconds=1)),
    ],
)
def test_non_explicit_or_inactive_grants_are_not_commercially_eligible(
    grant: RightsGrant,
) -> None:
    assert is_commercially_eligible([grant], at=NOW) is False


def test_explicit_active_commercial_grant_is_eligible() -> None:
    assert is_commercially_eligible([_grant()], at=NOW) is True
