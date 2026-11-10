# Supabase client factory. Import get_supabase() wherever DB access is needed.
# Uses the service role key — never expose this key to the frontend.

from supabase import Client, create_client

from app.core.auth import current_identity
from app.core.config import settings

DEMO_TABLES = {
    name: f"demo_{name}" for name in (
        "research_objects", "runs", "results", "provenance_events", "research_folders",
    )
}


class BackendSetupError(RuntimeError):
    pass


class DemoDatabase:
    """Service-role demo access can never fall through to personal/legacy tables."""

    def __init__(self, client):
        self.client = client

    def table(self, name: str):
        if name not in DEMO_TABLES:
            raise ValueError("Table is outside the isolated demo workspace")
        return self.client.table(DEMO_TABLES[name])

    def rpc(self, name: str, params: dict):
        if name != "match_vault_chunks":
            raise ValueError("RPC is outside the public reference-vault scope")
        return self.client.rpc(name, params)


def get_supabase() -> Client | DemoDatabase:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise BackendSetupError("Database configuration is missing")
    client = create_client(settings.supabase_url, settings.supabase_service_key)
    if settings.access_mode == "demo":
        return DemoDatabase(client)
    identity = current_identity.get()
    if identity is not None:
        # The user JWT replaces service-role authorization on every DB/RPC call.
        # Migration 008 enforces ownership, including results and provenance.
        client.postgrest.auth(identity.access_token)
    return client
