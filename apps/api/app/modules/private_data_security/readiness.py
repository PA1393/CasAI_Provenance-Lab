"""Deterministic private-data readiness evidence and fail-closed decisions."""

from __future__ import annotations

import json
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.modules.information_processor.contracts import Contract, checksum

SecurityControl = Literal[
    "authentication",
    "multi_factor_authentication",
    "tenant_isolation",
    "row_level_security",
    "encryption",
    "signed_expiring_downloads",
    "audit_logging",
    "retention_and_deletion",
    "malware_scanning",
    "consent_and_rights_enforcement",
    "independent_penetration_test",
    "privacy_review",
    "incident_response",
]
ControlStatus = Literal["not_implemented", "implemented", "independently_verified"]
DataSensitivity = Literal[
    "casai_synthetic",
    "public_non_sensitive",
    "customer_private",
    "unknown",
]
SensitiveOperation = Literal["ingest", "process", "export", "delete"]

REQUIRED_PRIVATE_DATA_CONTROLS: tuple[SecurityControl, ...] = SecurityControl.__args__


def _identity(values: dict[str, object]) -> str:
    return checksum(
        json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


class ControlAttestation(Contract):
    control: SecurityControl
    status: ControlStatus
    evidence_ids: tuple[str, ...] = ()
    assessor: str | None = Field(default=None, min_length=1, max_length=128)
    assessed_on: date | None = None
    expires_on: date | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> ControlAttestation:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Security evidence identities must be unique")
        if any(
            not evidence.startswith("sha256:")
            or len(evidence) != 71
            or any(character not in "0123456789abcdef" for character in evidence[7:])
            for evidence in self.evidence_ids
        ):
            raise ValueError("Security evidence must use SHA-256 identities")
        if self.status == "independently_verified":
            if (
                not self.evidence_ids
                or not self.assessor
                or not self.assessor.strip()
                or not self.assessed_on
            ):
                raise ValueError("Independent verification requires evidence and an assessor")
        if self.expires_on and not self.assessed_on:
            raise ValueError("Expiring evidence requires an assessment date")
        if self.expires_on and self.expires_on < self.assessed_on:
            raise ValueError("Security evidence cannot expire before assessment")
        return self


class ReadinessReport(Contract):
    schema_version: Literal["casai.private-data-readiness.v1"] = (
        "casai.private-data-readiness.v1"
    )
    report_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    as_of: date
    attestations: tuple[ControlAttestation, ...]
    missing_controls: tuple[SecurityControl, ...]
    unverified_controls: tuple[SecurityControl, ...]
    expired_controls: tuple[SecurityControl, ...]
    eligible: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_report(self) -> ReadinessReport:
        controls = tuple(attestation.control for attestation in self.attestations)
        if len(set(controls)) != len(controls):
            raise ValueError("Readiness attestations must contain each control at most once")
        expected_missing = tuple(
            control for control in REQUIRED_PRIVATE_DATA_CONTROLS if control not in controls
        )
        expected_expired = tuple(
            attestation.control
            for attestation in self.attestations
            if attestation.expires_on is not None and attestation.expires_on < self.as_of
        )
        expected_unverified = tuple(
            attestation.control
            for attestation in self.attestations
            if attestation.status != "independently_verified"
            or attestation.assessed_on is None
            or attestation.assessed_on > self.as_of
        )
        if self.missing_controls != expected_missing:
            raise ValueError("Missing-control summary does not match attestations")
        if self.unverified_controls != expected_unverified:
            raise ValueError("Unverified-control summary does not match attestations")
        if self.expired_controls != expected_expired:
            raise ValueError("Expired-control summary does not match attestations")
        expected_eligible = not (
            expected_missing or expected_unverified or expected_expired
        )
        if self.eligible != expected_eligible:
            raise ValueError("Private-data eligibility must derive from control evidence")
        identity = self.model_dump(mode="json", exclude={"report_id"})
        if self.report_id != _identity(identity):
            raise ValueError("Readiness identity must match canonical evidence content")
        return self


class AccessDecision(Contract):
    sensitivity: DataSensitivity
    operation: SensitiveOperation
    allowed: bool = Field(strict=True)
    code: Literal[
        "public_demo_allowed",
        "private_controls_verified",
        "private_controls_incomplete",
        "unknown_sensitivity_blocked",
    ]
    readiness_report_id: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_decision(self) -> AccessDecision:
        expected_allowed = self.code in {
            "public_demo_allowed",
            "private_controls_verified",
        }
        if self.allowed != expected_allowed:
            raise ValueError("Access decision must match its reason code")
        if self.sensitivity == "customer_private" and self.readiness_report_id is None:
            raise ValueError("Private-data decisions require a readiness report")
        if self.sensitivity != "customer_private" and self.readiness_report_id is not None:
            raise ValueError("Non-private decisions cannot reference private readiness")
        return self


class PrivateDataBlockedError(RuntimeError):
    def __init__(self, decision: AccessDecision) -> None:
        self.decision = decision
        super().__init__(decision.code)


def evaluate_readiness(
    attestations: tuple[ControlAttestation, ...],
    *,
    as_of: date,
) -> ReadinessReport:
    controls = tuple(attestation.control for attestation in attestations)
    if len(set(controls)) != len(controls):
        raise ValueError("Readiness attestations must contain each control at most once")
    ordered = tuple(
        attestation
        for control in REQUIRED_PRIVATE_DATA_CONTROLS
        for attestation in attestations
        if attestation.control == control
    )
    missing = tuple(
        control for control in REQUIRED_PRIVATE_DATA_CONTROLS if control not in controls
    )
    unverified = tuple(
        attestation.control
        for attestation in ordered
        if attestation.status != "independently_verified"
        or attestation.assessed_on is None
        or attestation.assessed_on > as_of
    )
    expired = tuple(
        attestation.control
        for attestation in ordered
        if attestation.expires_on is not None and attestation.expires_on < as_of
    )
    values: dict[str, object] = {
        "schema_version": "casai.private-data-readiness.v1",
        "as_of": as_of.isoformat(),
        "attestations": [item.model_dump(mode="json") for item in ordered],
        "missing_controls": list(missing),
        "unverified_controls": list(unverified),
        "expired_controls": list(expired),
        "eligible": not (missing or unverified or expired),
    }
    return ReadinessReport(report_id=_identity(values), **values)


def authorize_sensitive_operation(
    *,
    sensitivity: DataSensitivity,
    operation: SensitiveOperation,
    readiness: ReadinessReport | None = None,
) -> AccessDecision:
    if sensitivity in {"casai_synthetic", "public_non_sensitive"}:
        return AccessDecision(
            sensitivity=sensitivity,
            operation=operation,
            allowed=True,
            code="public_demo_allowed",
        )
    if sensitivity == "unknown":
        return AccessDecision(
            sensitivity=sensitivity,
            operation=operation,
            allowed=False,
            code="unknown_sensitivity_blocked",
        )
    if readiness is None:
        raise ValueError("Customer-private decisions require a readiness report")
    return AccessDecision(
        sensitivity=sensitivity,
        operation=operation,
        allowed=readiness.eligible,
        code=(
            "private_controls_verified"
            if readiness.eligible
            else "private_controls_incomplete"
        ),
        readiness_report_id=readiness.report_id,
    )


def require_sensitive_operation(
    *,
    sensitivity: DataSensitivity,
    operation: SensitiveOperation,
    readiness: ReadinessReport | None = None,
) -> AccessDecision:
    decision = authorize_sensitive_operation(
        sensitivity=sensitivity,
        operation=operation,
        readiness=readiness,
    )
    if not decision.allowed:
        raise PrivateDataBlockedError(decision)
    return decision
