"""Private-data security readiness remains fail-closed until independently verified."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.modules.private_data_security import (
    ControlAttestation,
    PrivateDataBlockedError,
    authorize_sensitive_operation,
    evaluate_readiness,
    require_sensitive_operation,
)
from app.modules.private_data_security.readiness import REQUIRED_PRIVATE_DATA_CONTROLS

EVIDENCE = "sha256:" + "1" * 64
TODAY = date(2026, 10, 18)


def _verified(control, *, expires_on=date(2027, 10, 18)):
    return ControlAttestation(
        control=control,
        status="independently_verified",
        evidence_ids=(EVIDENCE,),
        assessor="independent-reviewer",
        assessed_on=date(2026, 10, 1),
        expires_on=expires_on,
    )


def _complete():
    return tuple(_verified(control) for control in REQUIRED_PRIVATE_DATA_CONTROLS)


def test_empty_readiness_report_is_ineligible_and_deterministic():
    first = evaluate_readiness((), as_of=TODAY)
    second = evaluate_readiness((), as_of=TODAY)

    assert first == second
    assert first.report_id == second.report_id
    assert first.eligible is False
    assert first.missing_controls == REQUIRED_PRIVATE_DATA_CONTROLS


def test_every_control_requires_independent_current_evidence():
    attestations = list(_complete())
    attestations[0] = ControlAttestation(
        control=REQUIRED_PRIVATE_DATA_CONTROLS[0],
        status="implemented",
    )
    attestations[1] = _verified(
        REQUIRED_PRIVATE_DATA_CONTROLS[1],
        expires_on=date(2026, 10, 17),
    )
    report = evaluate_readiness(tuple(reversed(attestations)), as_of=TODAY)

    assert report.eligible is False
    assert report.unverified_controls == (REQUIRED_PRIVATE_DATA_CONTROLS[0],)
    assert report.expired_controls == (REQUIRED_PRIVATE_DATA_CONTROLS[1],)
    assert tuple(item.control for item in report.attestations) == REQUIRED_PRIVATE_DATA_CONTROLS


def test_future_dated_verification_does_not_enable_readiness():
    attestations = list(_complete())
    attestations[0] = ControlAttestation(
        control=REQUIRED_PRIVATE_DATA_CONTROLS[0],
        status="independently_verified",
        evidence_ids=(EVIDENCE,),
        assessor="independent-reviewer",
        assessed_on=date(2026, 10, 19),
        expires_on=date(2027, 10, 19),
    )
    report = evaluate_readiness(tuple(attestations), as_of=TODAY)

    assert report.eligible is False
    assert report.unverified_controls == (REQUIRED_PRIVATE_DATA_CONTROLS[0],)


def test_complete_independently_verified_controls_enable_private_decision():
    readiness = evaluate_readiness(_complete(), as_of=TODAY)
    decision = authorize_sensitive_operation(
        sensitivity="customer_private",
        operation="process",
        readiness=readiness,
    )

    assert readiness.eligible is True
    assert decision.allowed is True
    assert decision.code == "private_controls_verified"
    assert decision.readiness_report_id == readiness.report_id


def test_private_operation_is_blocked_when_controls_are_incomplete():
    readiness = evaluate_readiness((), as_of=TODAY)
    with pytest.raises(PrivateDataBlockedError) as caught:
        require_sensitive_operation(
            sensitivity="customer_private",
            operation="ingest",
            readiness=readiness,
        )
    assert caught.value.decision.code == "private_controls_incomplete"


def test_unknown_sensitivity_is_blocked_and_public_demo_data_is_allowed():
    blocked = authorize_sensitive_operation(
        sensitivity="unknown",
        operation="ingest",
    )
    allowed = require_sensitive_operation(
        sensitivity="casai_synthetic",
        operation="process",
    )

    assert blocked.allowed is False
    assert blocked.code == "unknown_sensitivity_blocked"
    assert allowed.allowed is True
    assert allowed.code == "public_demo_allowed"


def test_private_decision_cannot_bypass_missing_readiness():
    with pytest.raises(ValueError, match="readiness report"):
        authorize_sensitive_operation(
            sensitivity="customer_private",
            operation="export",
        )


def test_independent_verification_requires_evidence_assessor_and_date():
    with pytest.raises(ValidationError, match="requires evidence"):
        ControlAttestation(
            control="authentication",
            status="independently_verified",
        )
    with pytest.raises(ValidationError, match="SHA-256"):
        ControlAttestation(
            control="authentication",
            status="independently_verified",
            evidence_ids=("ticket-123",),
            assessor="reviewer",
            assessed_on=TODAY,
        )


def test_duplicate_attestations_are_rejected():
    attestation = _verified("authentication")
    with pytest.raises(ValueError, match="at most once"):
        evaluate_readiness((attestation, attestation), as_of=TODAY)
