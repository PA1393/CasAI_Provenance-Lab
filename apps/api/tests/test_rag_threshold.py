from unittest.mock import MagicMock

from app.core.config import settings
from app.modules.rag import service


def test_default_threshold_is_tuned_value() -> None:
    # Pin the tuned default so it can't silently regress. Relevant queries score
    # ~0.55-0.73 against the vault and off-topic ones ~0.17, so 0.25 is the floor
    # that drops noise without trimming real matches.
    assert settings.rag_match_threshold == 0.25


def test_search_vault_forwards_default_threshold_to_rpc(monkeypatch) -> None:
    # Offline: fake the embedding + Supabase so we assert only our own glue — that
    # search_vault passes the configured threshold through to match_vault_chunks.
    monkeypatch.setattr(service, "embed_query", lambda text: [0.1] * 1536)
    fake_sb = MagicMock()
    fake_sb.rpc.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(service, "get_supabase", lambda: fake_sb)

    service.search_vault("maize waxy Wx1")  # no threshold arg -> uses the default

    fake_sb.rpc.assert_called_once()
    name, params = fake_sb.rpc.call_args.args
    assert name == "match_vault_chunks"
    assert params["match_threshold"] == settings.rag_match_threshold
