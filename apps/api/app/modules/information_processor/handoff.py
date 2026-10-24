"""Explicit confirmed-sequence downloads and a lossless legacy run-input bridge."""

from uuid import NAMESPACE_URL, uuid5

from app.modules.information_processor.confirmation import ConfirmedResearchObject
from app.modules.information_processor.contracts import checksum
from app.modules.information_processor.workspace import LocalWorkspace
from app.modules.research_objects.service import create_research_object, get_research_object


def export_confirmed_fasta(version: ConfirmedResearchObject) -> dict:
    lines = []
    for record in version.snapshot.records:
        # Headers remain one line. Original record IDs and separate records are retained.
        description = " ".join((record.description.value or "").split())
        lines.append(
            f">{record.record_id.value} casai_version={version.version_id} "
            f"molecule={record.molecule_type.value} record_checksum={record.checksum} "
            f"source_checksum={version.original_artifact.checksum}"
            + (f" | {description}" if description else "")
        )
        sequence = record.sequence.value
        lines.extend(sequence[start:start + 80] for start in range(0, len(sequence), 80))
    content = "\n".join(lines) + "\n"
    return {
        "schema_version": "casai.confirmed-fasta.v1", "version_id": version.version_id,
        "filename": f"casai-confirmed-{version.version_id.removeprefix('sha256:')}.fasta",
        "content": content, "byte_length": len(content.encode("utf-8")),
        "checksum": checksum(content.encode("utf-8")),
        "normalized_checksum": version.normalized_checksum,
        "original_artifact_checksum": version.original_artifact.checksum,
        "record_count": len(version.snapshot.records),
        "claim_type": version.original_artifact.claim_type,
        "warning_codes": [notice.code for notice in version.snapshot.warnings],
    }


def selected_sequence(version: ConfirmedResearchObject, record_id: str) -> str:
    record = next((r for r in version.snapshot.records if r.record_id.value == record_id), None)
    if record is None:
        raise ValueError("Choose an exact record from this confirmed version")
    if record.molecule_type.value != "DNA":
        raise ValueError("The current run engine requires DNA; RNA conversion must be explicit")
    sequence = record.sequence.value
    if set(sequence) - set("ACGT"):
        raise ValueError("The current run handoff requires unambiguous A/C/G/T DNA")
    if len(sequence) > 5_000:
        raise ValueError("The demo run handoff is limited to 5,000 bases; select a smaller input")
    return sequence


def validate_run_source(row: dict, workspace: LocalWorkspace) -> None:
    version_id = row.get("confirmed_version_id")
    record_id = row.get("confirmed_record_id")
    if not version_id and not record_id:
        return  # Existing legacy FASTA records remain usable.
    if not version_id or not record_id:
        raise ValueError("Confirmed run-input linkage is incomplete")
    version = workspace.load_confirmed_version(version_id)
    sequence = selected_sequence(version, record_id)
    if row.get("sequence") != sequence or row.get("ro_hash") != checksum(sequence.encode("ascii")):
        raise ValueError("Run input no longer matches the confirmed sequence")


def prepare_run_input(
    workspace: LocalWorkspace, version_id: str, record_id: str, name: str,
) -> dict:
    version = workspace.load_confirmed_version(version_id)
    sequence = selected_sequence(version, record_id)
    identity = str(uuid5(NAMESPACE_URL, f"casai:confirmed:{version_id}:{record_id}"))

    def verified(row):
        if (row.get("confirmed_version_id") != version_id
                or row.get("confirmed_record_id") != record_id):
            raise ValueError("Existing run input has a different source binding")
        validate_run_source(row, workspace)
        return row

    existing = get_research_object(identity)
    if existing:
        return verified(existing)
    payload = {
        "research_object_id": identity, "name": name,
        "input_filename": "confirmed-record.fasta", "input_file_type": "fasta", "pdb_id": "",
        "fasta_text": f">confirmed_record\n{sequence}\n",
        "confirmed_version_id": version_id, "confirmed_record_id": record_id,
    }
    try:
        created = create_research_object(payload)
    except Exception:
        # A concurrent request can win the unique-key insert. Reopen only an
        # exact source match; never update/overwrite an existing input or run.
        winner = get_research_object(identity)
        if winner:
            return verified(winner)
        raise
    return verified(created)
