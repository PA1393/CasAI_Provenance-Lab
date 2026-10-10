from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.rights.service import is_commercially_eligible
from app.schemas.contracts import (
    PermissionBasis,
    RightsGrant,
    RightsScope,
    RightsStatus,
)

NOW = datetime(2026, 10, 9, tzinfo=UTC)


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
