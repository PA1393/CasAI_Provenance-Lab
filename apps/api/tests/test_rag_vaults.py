from unittest.mock import MagicMock

from app.core.config import settings
from app.modules.rag import service


def test_select_vaults_returns_configured_default() -> None:
    # Demo scope: routing always resolves to the single configured vault,
    # regardless of the prompt. Pins that behavior so a future LLM router
    # can't silently change the default path.
    assert service.select_vaults("anything about maize") == [settings.default_vault]


def test_default_vault_is_crop() -> None:
    # The demo is crop-only; guard the default so it can't drift unnoticed.
    assert settings.default_vault == "crop"


def _fake_supabase(monkeypatch):
    """Stub embedding + Supabase so we assert only our own glue, offline."""
    monkeypatch.setattr(service, "embed_query", lambda text: [0.1] * 1536)
    fake_sb = MagicMock()
    fake_sb.rpc.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(service, "get_supabase", lambda: fake_sb)
    return fake_sb


def test_search_vault_defaults_to_selected_vault(monkeypatch) -> None:
    # With no vaults arg, search_vault must route through select_vaults and pass
    # the resulting vault list to the RPC as vault_filter.
    fake_sb = _fake_supabase(monkeypatch)

    service.search_vault("maize waxy Wx1")

    fake_sb.rpc.assert_called_once()
    name, params = fake_sb.rpc.call_args.args
    assert name == "match_vault_chunks"
    assert params["vault_filter"] == [settings.default_vault]


def test_search_vault_forwards_explicit_vaults(monkeypatch) -> None:
    # An explicit vaults arg overrides routing and reaches the RPC unchanged.
    fake_sb = _fake_supabase(monkeypatch)

    service.search_vault("some query", vaults=["human", "crop"])

    _, params = fake_sb.rpc.call_args.args
    assert params["vault_filter"] == ["human", "crop"]
