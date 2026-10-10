from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from app.schemas.contracts import RightsGrant, RightsScope, RightsStatus


def is_commercially_eligible(
    grants: Iterable[RightsGrant], *, at: datetime | None = None
) -> bool:
    """Return whether an exact run/source/artifact version may enter a sellable pool.

    Visibility never implies commercial permission. Eligibility requires an active,
    explicit commercial grant that is in effect and has not expired or been revoked.
    """
    checked_at = at or datetime.now(UTC)
    return any(_is_valid_commercial_grant(grant, checked_at) for grant in grants)


def _is_valid_commercial_grant(grant: RightsGrant, checked_at: datetime) -> bool:
    return (
        grant.scope == RightsScope.COMMERCIAL_LICENSE
        and grant.status == RightsStatus.ACTIVE
        and grant.explicit_permission
        and grant.effective_at <= checked_at
        and (grant.expires_at is None or grant.expires_at > checked_at)
        and grant.revoked_at is None
    )
