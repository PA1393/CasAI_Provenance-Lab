"""Disposable test fixture: actual CasAI routes/engine, RAM DB; no hosted writes."""
import sys
import os
import tempfile

if __name__ != "__main__" or os.environ.get("CASAI_DISPOSABLE_REHEARSAL") != "1":
    raise RuntimeError("Test fixture only: explicitly set CASAI_DISPOSABLE_REHEARSAL=1")
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/api"))
from app.main import app
from app.core.config import settings
from app.api.routes import folders, runs as run_routes
from app.modules.research_objects import service as inputs
from app.modules.runs import service as runs
from app.modules.results import service as results
from app.modules.provenance import service as provenance
from app.api.dependencies import get_storage_backend

app.dependency_overrides[get_storage_backend] = lambda: "temporary"

settings.access_mode = "demo"
settings.openai_api_key = ""  # Never call hosted AI or silently obtain references.
fixture_directory = tempfile.TemporaryDirectory(prefix="casai-disposable-rehearsal-")
settings.intake_workspace_root = Path(fixture_directory.name)
for middleware in app.user_middleware:
    if middleware.cls.__name__ == "CORSMiddleware":
        middleware.kwargs["allow_origins"] = ["http://localhost:3105", "http://127.0.0.1:3105"]
keys = dict(research_objects="research_object_id", runs="run_id", results="result_id",
    provenance_events="event_id", research_folders="folder_id")
rows = {name: [] for name in keys}
class Query:
    def __init__(self, name):
        self.name, self.filters, self.single = name, [], False
        self.operation, self.payload = "select", None
    def select(self, *args, **kwargs): return self
    def eq(self, key, value): self.filters.append((key, value)); return self
    def order(self, *args, **kwargs): return self
    def maybe_single(self): self.single = True; return self
    def insert(self, payload): self.operation, self.payload = "insert", payload; return self
    def update(self, payload): self.operation, self.payload = "update", payload; return self
    def execute(self):
        selected = [row for row in rows[self.name] if all(row.get(k) == v for k, v in self.filters)]
        if self.operation == "insert":
            row = {keys[self.name]: str(uuid4()), "created_at": datetime.now(UTC).isoformat(),
                **self.payload}
            if self.name == "runs": row.setdefault("completed_at", None)
            rows[self.name].append(row); selected = [row]
        elif self.operation == "update":
            for row in selected: row.update(self.payload)
        return SimpleNamespace(data=(selected[0] if selected else None) if self.single else selected,
            count=len(selected))
database = SimpleNamespace(table=lambda name: Query(name))
@app.get("/__disposable_rehearsal__")
def fixture_marker():
    return {"disposable": True, "hosted_writes": False}
for module in [inputs, runs, results, provenance, folders, run_routes]:
    module.get_supabase = lambda: database
if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="127.0.0.1", port=8815)
    finally:
        fixture_directory.cleanup()
