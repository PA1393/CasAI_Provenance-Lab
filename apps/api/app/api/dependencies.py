"""Shared FastAPI dependencies for local demo services."""

from app.core.config import settings
from app.modules.information_processor.workspace import LocalWorkspace


def get_intake_workspace() -> LocalWorkspace:
    """Construct the configured local store; dependency overrides isolate tests."""

    return LocalWorkspace(settings.intake_workspace_root)
