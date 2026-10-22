"""Fail-closed readiness gates for future private-data deployments."""

from app.modules.private_data_security.readiness import (
    AccessDecision,
    ControlAttestation,
    PrivateDataBlockedError,
    ReadinessReport,
    authorize_sensitive_operation,
    evaluate_readiness,
    require_sensitive_operation,
)

__all__ = [
    "AccessDecision",
    "ControlAttestation",
    "PrivateDataBlockedError",
    "ReadinessReport",
    "authorize_sensitive_operation",
    "evaluate_readiness",
    "require_sensitive_operation",
]
