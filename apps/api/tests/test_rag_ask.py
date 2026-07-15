from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes import rag as rag_routes
from app.main import app
from app.modules.rag import service
from app.schemas.rag import RagAskRequest, RagSearchRequest

client = TestClient(app)


def _make_chunk(chunk_id: str = "c1") -> dict:
    return {
        "chunk_id": chunk_id,
        "source_key": "doc-1",
        "chunk_text": "CRISPR-Cas9 enables targeted genome editing.",
        "metadata": None,
        "similarity": 0.87,
        "source_path": "papers/doc-1.pdf",
        "source_url": None,
        "source_title": "Doc One",
        "source_type": "paper",   
    }
def test_rag_ask_request_inherits_search_request() -> None:
    assert issubclass(RagAskRequest, RagSearchRequest)


def test_rag_ask_request_caps_match_count() -> None:
    body = RagAskRequest(query="q", match_count=999)
    assert body.match_count == 5


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_rag_ask_request_rejects_out_of_range_threshold(threshold: float) -> None:
    with pytest.raises(ValidationError):
        RagAskRequest(query="q", match_threshold=threshold)


def test_rag_ask_request_accepts_boundary_thresholds() -> None:
    low = RagAskRequest(query="q", match_threshold=0.0)
    high = RagAskRequest(query="q", match_threshold=1.0)
    assert low.match_threshold == 0.0
    assert high.match_threshold == 1.0


def test_generate_answer_returns_none_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "openai_api_key", "")
    result = service.generate_answer("query", [_make_chunk()])
    assert result is None


def test_generate_answer_returns_none_without_chunks(monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "openai_api_key", "test-key")
    result = service.generate_answer("query", [])
    assert result is None


def test_generate_answer_returns_text_on_success(monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "openai_api_key", "test-key")
    message = MagicMock(content="Grounded answer [1].")
    mock_response = MagicMock(choices=[MagicMock(message=message)])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr(service, "OpenAI", lambda api_key: mock_client)
    result = service.generate_answer("query", [_make_chunk()])
    assert result == "Grounded answer [1]."


def test_generate_answer_returns_none_on_api_error(monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "openai_api_key", "test-key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("boom")
    monkeypatch.setattr(service, "OpenAI", lambda api_key: mock_client)
    result = service.generate_answer("query", [_make_chunk()])
    assert result is None


def test_answer_query_combines_sources_and_answer(monkeypatch) -> None:
    chunks = [_make_chunk("c1"), _make_chunk("c2")]
    monkeypatch.setattr(service, "search_vault", lambda **kwargs: chunks)
    monkeypatch.setattr(service, "generate_answer", lambda query, chunks: "Answer text")
    result = service.answer_query("query")
    assert result == {"answer": "Answer text", "sources": chunks}


def test_rag_ask_endpoint_returns_answer_and_sources(monkeypatch) -> None:
    fake_result = {"answer": "Grounded answer.", "sources": [_make_chunk()]}
    monkeypatch.setattr(rag_routes, "answer_query", lambda **kwargs: fake_result)
    response = client.post("/api/v1/rag/ask", json={"query": "What is CRISPR?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Grounded answer."
    assert len(body["sources"]) == 1


def test_rag_ask_endpoint_allows_null_answer(monkeypatch) -> None:
    fake_result = {"answer": None, "sources": []}
    monkeypatch.setattr(rag_routes, "answer_query", lambda **kwargs: fake_result)
    response = client.post("/api/v1/rag/ask", json={"query": "Unanswerable question"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None
    assert body["sources"] == []


def test_rag_ask_endpoint_rejects_invalid_match_threshold() -> None:
    response = client.post("/api/v1/rag/ask", json={"query": "q", "match_threshold": 5.0})
    assert response.status_code == 422
