# Setup

## Web

Install workspace dependencies from the repo root:

```bash
bun install
```

Run the frontend from the repo root:

```bash
bun run dev:web
```

Default frontend URL: `http://localhost:3000`

The frontend reads the backend base URL from `NEXT_PUBLIC_API_BASE_URL`.
If you do not set it, the shared env helper defaults to `http://127.0.0.1:8000`.

## API

Create the backend virtual environment:

```bash
cd apps/api
python -m venv .venv
```

### Windows PowerShell

Create and activate the virtual environment:

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install -e .[dev]
```

Run the backend:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Run backend tests:

```powershell
python -m pytest
```

Lint backend code:

```powershell
python -m ruff check .
```

### macOS/Linux

Create and activate the virtual environment:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
python -m pip install -e .[dev]
```

Run the backend:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Run backend tests:

```bash
python -m pytest
```

Lint backend code:

```bash
python -m ruff check .
```

Default backend URL: `http://127.0.0.1:8000`

## Cross-Platform Root Commands

Once the backend virtual environment has been created at `apps/api/.venv` and the editable install is complete, these root commands work from the repo root on both Windows and macOS/Linux:

```bash
bun run dev:web
bun run dev:api
bun run check:web
bun run lint:api
bun run test:api
bun run check:api
```

The API commands resolve `apps/api/.venv` directly instead of relying on `python` from `PATH`.

## Route Convention

- Health stays unversioned: `GET /health`
- App routes use an early versioned prefix: `GET /api/v1/runs`
