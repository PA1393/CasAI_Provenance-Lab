"""Pipeline wiring tests for create_run() — proves the real analysis -> validate
-> engine -> score chain runs and emits per-stage provenance, using a fake
Supabase so no live DB, OpenAI key, or network is needed."""

import pytest

from app.modules.provenance import service as prov_service
from app.modules.runs import service
from app.modules.simulation.spec import EditSpec


class _Resp:
    def __init__(self, data):
        self.data = data


class _Builder:
    def __init__(self, sb, table):
        self.sb, self.table = sb, table
        self._op = self._payload = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, row):
        self._op, self._payload = "insert", row
        return self

    def update(self, patch):
        self._op, self._payload = "update", patch
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return self.sb.run(self.table, self._op, self._payload)


class FakeSupabase:
    def __init__(self, ro):
        self.ro = ro
        self.run_row = {}
        self.inserts = {"runs": [], "results": [], "provenance_events": []}
        self.run_updates = []
        self.events = []  # provenance event payloads, in emit order

    def table(self, name):
        return _Builder(self, name)

    def run(self, table, op, payload):
        if op == "insert":
            self.inserts.setdefault(table, []).append(payload)
            if table == "runs":
                self.run_row = {**payload, "run_id": "run-1"}
                return _Resp([self.run_row])
            if table == "provenance_events":
                self.events.append(payload)
            return _Resp([payload])
        if op == "update":  # runs only
            self.run_row = {**self.run_row, **payload}
            self.run_updates.append(payload)
            return _Resp([self.run_row])
        if op == "select":
            if table == "research_objects":
                return _Resp(self.ro)
            if table == "runs":
                return _Resp(self.run_row)
        return _Resp(None)


# A short sequence containing a real 20-nt protospacer + NGG PAM with an
# editable C in the CBE window (positions 4-8), so the engine makes a real edit.
_GUIDE = "ACGTACGTACGTACGTACGT"
_SEQUENCE = "TT" + _GUIDE + "CGG" + "TT"  # guide at index 2, PAM "CGG" immediately 3'


def test_unverifiable_confirmed_source_blocks_before_run_insert(monkeypatch, tmp_path):
    from app.modules.information_processor.workspace import LocalWorkspace

    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE,
                           "confirmed_version_id": "sha256:" + "a" * 64,
                           "confirmed_record_id": "record"})
    monkeypatch.setattr(service, "get_intake_workspace", lambda: LocalWorkspace(tmp_path / "empty"))
    with pytest.raises(service.ConfirmedSourceError, match="no run was submitted"):
        service.create_run("ro-1", "CBE edit")
    assert sb.inserts["runs"] == []


def test_confirmed_source_binding_is_recorded_in_pipeline_provenance(monkeypatch):
    spec = EditSpec(edit_type="CBE", guide_rna=_GUIDE, strand="+", rationale="test")
    ro = {"research_object_id": "ro-1", "sequence": _SEQUENCE,
          "confirmed_version_id": "sha256:" + "a" * 64, "confirmed_record_id": "record"}
    sb = _wire(monkeypatch, ro, spec=spec, problems=[])
    seen = []
    monkeypatch.setattr(service, "get_intake_workspace", lambda: object())
    monkeypatch.setattr(service, "validate_run_source", lambda row, _: seen.append(row))
    service.create_run("ro-1", "CBE edit")
    event = next(event for event in sb.events if event["event_type"] == "input_validated")
    assert seen == [ro]
    assert event["payload"]["confirmed_version_id"] == ro["confirmed_version_id"]
    assert event["payload"]["confirmed_record_id"] == "record"


def _wire(monkeypatch, ro, *, spec=None, problems=None):
    sb = FakeSupabase(ro)
    monkeypatch.setattr(service, "get_supabase", lambda: sb)
    monkeypatch.setattr(prov_service, "get_supabase", lambda: sb)
    if spec is not None:
        monkeypatch.setattr(service, "resolve_edit_spec", lambda prompt, sequence: spec)
    if problems is not None:
        monkeypatch.setattr(service, "validate_edit_spec", lambda spec, sequence: problems)
    return sb


def _stages(sb):
    return [(e["stage"], e["event_type"]) for e in sb.events]


@pytest.mark.parametrize("mode,index,replacement", [("demo_cbe", 7, "T"), ("demo_abe", 6, "G")])
def test_rule_based_demo_runs_real_engine_without_ai(monkeypatch, mode, index, replacement):
    def forbidden(*args, **kwargs):
        raise AssertionError("Rule-based mode must never call AI/retrieval")

    outcomes = []
    for label in ["Software review", "Do not interpret this as a gene objective"]:
        sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE})
        monkeypatch.setattr(service, "resolve_edit_spec", forbidden)
        result = service.create_run("ro-1", label, mode)
        assert result["status"] == "completed"
        assert result["guide_rna"] == _GUIDE
        outcome = sb.inserts["results"][0]
        assert outcome["edited_sequence"] == _SEQUENCE[:index] + replacement + _SEQUENCE[index + 1:]
        assert "No AI or retrieval" in outcome["notes"]
        assert sb.events[0]["payload"]["execution_mode"] == mode
        assert sb.events[0]["payload"]["target_region_policy"] == "metadata_only_full_sequence"
        intent = next(event for event in sb.events if event["event_type"] == "intent_resolved")
        assert intent["payload"]["pam"] == "NGG" and intent["payload"]["window"] == [4, 8]
        outcomes.append(outcome["edited_sequence"])
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("mode,positions,base", [("demo_cbe", [8, 10], "T"),
                                               ("demo_abe", [9, 11, 12], "G")])
def test_distributed_demo_fixture_has_known_edits(monkeypatch, mode, positions, base):
    from pathlib import Path

    from app.modules.research_objects.fasta import parse_fasta

    fixture = Path(__file__).resolve().parents[3] / "test-fixtures/desktop-demo/synthetic-cbe.fasta"
    sequence = parse_fasta(fixture.read_text())["sequence"]
    sb = _wire(monkeypatch, {"research_object_id": "fixture", "sequence": sequence})
    result = service.create_run("fixture", "Distributed synthetic fixture", mode)
    assert result["status"] == "completed"
    expected = list(sequence)
    for position in positions:
        expected[position - 1] = base
    assert sb.inserts["results"][0]["edited_sequence"] == "".join(expected)


def test_demo_no_site_reports_failure_without_fabricated_results(monkeypatch):
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": "AT" * 20})
    result = service.create_run("ro-1", "No PAM", "demo_cbe")
    assert result["status"] == "failed"
    assert not sb.inserts["results"]
    assert "no compatible" in sb.events[-1]["message"].lower()
    assert result["failure"]["stage"] == "extract"
    assert result["failure"]["code"] == "no_compatible_site"


@pytest.mark.parametrize("sequence,mode", [("A" * 5001, "assisted"),
                                          ("ACNT", "demo_cbe"), ("", "demo_abe")])
def test_demo_constraints_reject_before_creating_a_run(monkeypatch, sequence, mode):
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": sequence})
    with pytest.raises(service.RunInputError):
        service.create_run("ro-1", "Invalid input", mode)
    assert not sb.inserts["runs"]


def test_run_request_bounds_and_demo_capabilities():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    capabilities = client.get("/api/v1/demo/capabilities").json()
    assert capabilities["max_sequence_bases"] == 5000
    assert capabilities["scientifically_validated"] is False
    for changes in [{"execution_mode": "invented"}, {"prompt": " "},
                    {"prompt": "x" * 2001}, {"unexpected": "value"}]:
        response = client.post("/api/v1/runs", json={
            "research_object_id": "demo-input", "prompt": "Demo", **changes,
        })
        assert response.status_code == 422


def test_happy_path_runs_real_chain_and_completes(monkeypatch) -> None:
    spec = EditSpec(edit_type="CBE", guide_rna=_GUIDE, strand="+", rationale="grounded [1]")
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE},
               spec=spec, problems=[])

    run = service.create_run("ro-1", "knock out gene X with a C->T edit")

    assert _stages(sb) == [
        ("input", "input_validated"),
        ("extract", "intent_resolved"),
        ("extract", "schema_validated"),
        ("simulate", "simulation_executed"),
        ("score", "edit_scored"),
        ("results", "results_packaged"),
    ]
    # Real result persisted with real (not hardcoded) scores.
    result = sb.inserts["results"][0]
    assert 0.0 <= result["on_target_score"] <= 1.0
    assert 0.0 <= result["off_target_score"] <= 1.0
    assert result["edited_sequence"]  # non-empty, NOT NULL
    assert run["status"] == "completed"
    assert run["current_stage"] == "summary"


def test_schema_invalid_halts_and_marks_failed(monkeypatch) -> None:
    spec = EditSpec(edit_type="CBE", guide_rna=_GUIDE, strand="+")
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE},
               spec=spec, problems=["guide + NGG PAM not found on the + strand"])

    run = service.create_run("ro-1", "prompt")

    assert ("extract", "schema_invalid") in _stages(sb)
    assert ("simulate", "simulation_executed") not in _stages(sb)  # stopped before engine
    assert sb.inserts["results"] == []  # no result written on failure
    assert run["status"] == "failed"
    assert run["current_stage"] == "extract"


def test_missing_sequence_halts_at_input(monkeypatch) -> None:
    # The real gap: research objects don't persist a sequence yet. The pipeline
    # must fail honestly at input, not fabricate a result.
    sb = _wire(monkeypatch, {"research_object_id": "ro-1"})  # no "sequence"

    run = service.create_run("ro-1", "prompt")

    assert _stages(sb) == [("input", "input_invalid")]
    assert sb.inserts["results"] == []
    assert run["status"] == "failed"
    assert run["current_stage"] == "input"


def test_analysis_failure_halts_at_extract(monkeypatch) -> None:
    # resolve_edit_spec raises ValueError when no API key / no guide / unclear edit.
    def boom(prompt, sequence):
        raise ValueError("OPENAI_API_KEY not set — analysis agent unavailable")

    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE})
    monkeypatch.setattr(service, "resolve_edit_spec", boom)

    run = service.create_run("ro-1", "prompt")

    assert ("extract", "analysis_failed") in _stages(sb)
    assert sb.inserts["results"] == []
    assert run["status"] == "failed"
    assert run["current_stage"] == "extract"


def test_analysis_network_error_is_still_classified_as_extract_failure(monkeypatch) -> None:
    # Not every analysis failure is a ValueError (missing key, bad JSON) — an
    # OpenAI network/rate-limit error is a different exception type. It must
    # still be caught and attributed to "extract", not fall through unhandled.
    def boom(prompt, sequence):
        raise RuntimeError("connection reset")

    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE})
    monkeypatch.setattr(service, "resolve_edit_spec", boom)

    run = service.create_run("ro-1", "prompt")

    assert ("extract", "analysis_failed") in _stages(sb)
    assert run["status"] == "failed"
    assert run["current_stage"] == "extract"


def test_unexpected_error_marks_run_failed_and_reraises(monkeypatch) -> None:
    # A truly unexpected failure (engine bug, DB hiccup) is not a _PipelineHalt.
    # The run must not be left stuck at status="running" forever, and the
    # caller must still see the error rather than a silently "successful" run.
    spec = EditSpec(edit_type="CBE", guide_rna=_GUIDE, strand="+")
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE},
               spec=spec, problems=[])

    def boom(*a, **k):
        raise RuntimeError("unexpected engine bug")

    monkeypatch.setattr(service, "apply_base_edit", boom)

    with pytest.raises(RuntimeError, match="unexpected engine bug"):
        service.create_run("ro-1", "prompt")

    # create_run raised, so there's no return value — inspect the fake DB directly.
    assert sb.run_row["status"] == "failed"
    assert sb.run_row["current_stage"] == "simulate"  # where _advance last landed
    assert sb.inserts["results"] == []
    assert sb.run_row["failure"]["stage"] == "simulate"
    assert sb.run_row["failure"]["code"] == "unexpected_error"
    assert "unexpected engine bug" not in sb.run_row["failure"]["message"]


@pytest.mark.parametrize("code", [
    "vault_no_evidence", "vault_unavailable", "vault_not_configured", "intent_unclear",
    "ai_unavailable", "intent_invalid", "no_compatible_site",
])
def test_analysis_failures_record_distinct_safe_reasons(monkeypatch, code):
    from app.modules.simulation.spec import AnalysisIssue
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE})
    def blocked(*args):
        raise AnalysisIssue(code)
    monkeypatch.setattr(service, "resolve_edit_spec", blocked)
    run = service.create_run("ro-1", "Explicit test objective")
    assert run["status"] == "failed"
    assert run["failure"]["code"] == code
    assert run["failure"]["next_step"]
    assert sb.events[-1]["payload"]["failure"] == run["failure"]
    assert not sb.inserts["results"]


def test_no_edit_is_not_recorded_as_a_successful_edit(monkeypatch):
    candidate = EditSpec(edit_type="CBE", guide_rna=_GUIDE, strand="+")
    sb = _wire(monkeypatch, {"research_object_id": "ro-1", "sequence": _SEQUENCE},
               spec=candidate, problems=[])
    monkeypatch.setattr(service, "apply_base_edit", lambda *a, **kw: {
        "edited": False, "reason": "no editable base",
    })
    run = service.create_run("ro-1", "No edit")
    assert run["failure"]["stage"] == "simulate"
    assert run["failure"]["code"] == "simulation_no_edit"
    assert not sb.inserts["results"]
