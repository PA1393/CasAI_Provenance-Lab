"""Shared FastAPI dependencies for local demo services."""

from typing import Literal

from app.core.auth import current_identity
from app.core.config import settings
from app.modules.information_processor.workspace import LocalWorkspace


def get_storage_backend() -> Literal["supabase", "temporary"]:
    """Describe the configured adapter, not its health or persistence guarantee."""
    return "supabase"


def get_intake_workspace() -> LocalWorkspace:
    """Construct the configured local store; dependency overrides isolate tests."""

    identity = current_identity.get()
    root = settings.intake_workspace_root
    if settings.access_mode == "demo":
        root = root / "demo"
    elif identity is not None:
        root = root / "users" / identity.user_id
    return LocalWorkspace(root)
