"""Allowlisted explanations, never raw upstream exception bodies or credentials."""
from pydantic import BaseModel, Field


class RunIssue(BaseModel):
    stage: str
    code: str
    message: str
    next_step: str
    details: list[str] = Field(default_factory=list)


_ISSUES = {
    "input_invalid": (
        "The saved research record has no usable sequence.",
        "Upload and review a supported FASTA before starting another run.",
    ),
    "no_compatible_site": (
        "No compatible guide, NGG PAM and editable base were found in the supplied sequence.",
        "Check the sequence and selected CBE/ABE editor, or try the synthetic example.",
    ),
    "vault_no_evidence": (
        "Vault search returned no relevant matches above the configured similarity threshold.",
        "Use a more specific crop/gene objective or ask the maintainer "
        "to add reviewed vault references. "
        "A rule-based CBE/ABE demo can run without the vault; it does not validate your objective.",
    ),
    "vault_not_configured": (
        "Vault retrieval is not configured, so evidence coverage could not be checked.",
        "Configure the embedding provider and reference vault, or use a rule-based demo.",
    ),
    "vault_unavailable": (
        "The reference vault or embedding service could not be reached. Coverage is unknown.",
        "Check the provider, database and network, then retry. "
        "Do not treat this as missing evidence.",
    ),
    "intent_unclear": (
        "The objective and retrieved evidence did not resolve a supported CBE or ABE edit.",
        "Specify the crop, gene and intended base conversion. No biological details were guessed.",
    ),
    "intent_invalid": (
        "The analysis response did not meet the required structured edit format.",
        "Refine the objective and retry, or select an explicit rule-based demo.",
    ),
    "ai_unavailable": (
        "The AI interpretation service could not complete the request.",
        "Check AI configuration, provider limits and network, or use a rule-based demo.",
    ),
    "analysis_unavailable": (
        "Analysis could not resolve an executable edit. The underlying cause was not classified.",
        "Review the objective and deployment configuration, or use an explicit rule-based demo.",
    ),
    "schema_invalid": (
        "The candidate edit did not pass sequence, guide, PAM or editing-window validation.",
        "Review the validation details in Provenance. The candidate was not executed.",
    ),
    "simulation_no_edit": (
        "The editing engine applied no edit to the supplied sequence.",
        "Check the guide, PAM and editable base window. No successful edit was recorded.",
    ),
    "unexpected_error": (
        "Processing stopped unexpectedly at this stage; later stages did not complete.",
        "Inspect the recorded stages and contact the demo maintainer. "
        "Do not resubmit until you have checked whether a run or result was already saved.",
    ),
}


def run_issue(stage: str, code: str) -> RunIssue:
    if code not in _ISSUES:
        code = "unexpected_error"
    message, next_step = _ISSUES[code]
    return RunIssue(stage=stage, code=code, message=message, next_step=next_step)
