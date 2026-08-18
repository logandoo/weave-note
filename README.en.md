# weave-note

> English (default) · [中文版](README.md)

A **standalone note-taking application**: capture, organize and search personal knowledge, with multi-format export.

## Highlights

- **Zero-config start**: SQLite by default (DB auto-created on first launch); switch to PostgreSQL with a one-line `[database] type` change
- **Lightweight & embeddable**: FastAPI + async SQLAlchemy 2.0 single process; Vue3 + Vite SPA frontend
- **Knowledge organization**: notebook → note two-level hierarchy, default notebook, quick notes, bulk operations
- **Full-text search**: title/body keyword search (cross-dialect ILIKE via SQLAlchemy), with notebook-scoped filtering
- **Multi-format export**: per-note Markdown, notebook CSV (ZIP), PDF (WeasyPrint)
- **Async export pipeline**: export tasks run in a background `export_worker` queue (concurrency 2, timeout 600s) — large exports never block the API
- **File parsing**: upload docx / pptx / xlsx / PDF / images and auto-parse into note body (lazy imports, graceful degradation when a dependency is missing)
- **Multi-user**: register/login/JWT, per-user `user_workspaces/` file areas

## Core Features

| Feature | Description |
|---|---|
| Notebook management | create / rename / set default / delete (default notebook protected) |
| Note CRUD | create / edit / move / bulk-delete |
| Quick note | one-click capture into the default notebook |
| Full-text search | keyword search with context snippets |
| Export | per-note Markdown / notebook CSV (ZIP) / PDF |
| File upload | docx/pptx/xlsx/PDF/image parsing |

## Directory Structure

```
weave-note/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry, health check, static files, export polling proxy
│   │   ├── api/             # routes: auth / notes / export_tasks / file_upload / image_upload
│   │   ├── core/            # config (sqlite/postgres dual mode) / deps
│   │   ├── db/              # database (dialect-adaptive engine) / migrations
│   │   ├── schemas/         # pydantic models
│   │   ├── services/        # auth_service / export_worker / file_parser / workspace_service etc.
│   │   └── vendor_js/       # third-party JS bundled with the frontend
│   ├── static/              # frontend build artifacts
│   ├── config.toml          # service config ([database] type switches sqlite/postgres)
│   └── requirements.txt
├── frontend/                # Vue3 + Vite source
└── scripts/                 # install_venv / init_db / build / start / stop / restart
```

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| OS | - | macOS / Ubuntu 22.04+ / Windows (WSL2 recommended; Git Bash on native Windows) |
| Python | 3.11+ (3.13 recommended) | Ubuntu 24.04 ships 3.12; 22.04: `add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12`; macOS: `brew install python@3.13`; Windows: python.org installer (check Add to PATH) |
| Node.js | 18+ (only to rebuild frontend) | Prebuilt `backend/static/` is committed; not required unless you change the frontend. If needed: macOS: `brew install node`; Ubuntu: `sudo apt install nodejs npm` (24.04 ships 18) or NodeSource; Windows: `winget install OpenJS.NodeJS.LTS` |
| curl | - | API verification |

> Database defaults to **SQLite** (zero external dependencies, auto-created on first launch).
> To switch to PostgreSQL 14+ (no pgvector needed), first install PostgreSQL:
> macOS: `brew install postgresql@16 && brew services start postgresql@16`;
> Ubuntu: `sudo apt install postgresql && sudo systemctl start postgresql`;
> Windows: use WSL2 and follow the Ubuntu steps.
> Then change `[database] type = "postgres"` in `backend/config.toml` and create the database:
>
> ```bash
> createdb -U postgres -h 127.0.0.1 weave_note
> ```
>
> Authentication notes: macOS/Homebrew uses trust auth locally (no password needed). Ubuntu's
> default local TCP auth is scram: first run `sudo -u postgres psql -c "ALTER USER postgres PASSWORD '<strong password>'"`,
> then `export PGPASSWORD='<strong password>'` when running scripts (init_db.sh passes it through),
> and write the same password into `[database] password` in `backend/config.toml`
> (the service reads config only, not environment variables).

### System dependencies for optional features (PDF export / chart rendering)

| Feature | System deps | Install |
|---|---|---|
| PDF export (WeasyPrint) | Pango libs | macOS: `brew install pango`; Ubuntu: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-noto-cjk` |
| Screenshot export (Playwright) | Chromium binary | After venv creation: `.venv/bin/python -m playwright install chromium` (`Scripts\python.exe` on Windows; add `python -m playwright install-deps chromium` on Ubuntu) |

> **Windows**: no official dependency-free WeasyPrint build for native Windows (needs Pango DLLs) — PDF export is unavailable there. Deploy weave-note inside WSL2 for full features; the rest works natively via Git Bash.

## Standalone Deployment (3 steps)

This project does not depend on any outer directory layout:

```bash
bash scripts/install_venv.sh   # project .venv + deps (idempotent; PYTHON_BIN to override interpreter)
bash scripts/init_db.sh        # initializes by [database] type: sqlite no-PG; postgres idempotent create+prebuild
bash scripts/start.sh          # start (auto-picks .venv)
curl http://127.0.0.1:8201/healthz
```

## Detailed Deployment

### 1. Database

**Recommended (self-contained)**: run the project script — it handles SQLite pre-create / PostgreSQL idempotent create + prebuild (repeatable):

```bash
bash scripts/init_db.sh
```

**SQLite (default)**: nothing to do; `backend/weave_note.db` is created on first launch.

**PostgreSQL (optional)**: requires local PostgreSQL 14+. The script idempotently runs `createdb weave_note`; or manually:

```bash
createdb -U postgres -h 127.0.0.1 weave_note
```

If the DB already exists, the error is ignorable, or check first:

```bash
psql -U postgres -h 127.0.0.1 -d postgres \
  -c "SELECT 1 FROM pg_database WHERE datname='weave_note'"
```

Inside the family monorepo you may also use the family entry (equivalent to running each project's `scripts/init_db.sh` in order; weave_mem is always PG+pgvector):

```bash
bash <family-root>/scripts/init_databases.sh
```

### 2. Virtual Environment

**Recommended (self-contained)**:

```bash
bash scripts/install_venv.sh
```

Equivalent manual steps:

```bash
python3.11 -m venv .venv     # or python3.13
./.venv/bin/pip install -r backend/requirements.txt
```

> If a shared venv already exists (e.g., family root `.venv` or `/tmp/weave-family-venv`),
> this step can be skipped; `scripts/start.sh` probes them in order.

### 3. Configuration

Edit `backend/config.toml`:

```toml
[server]
host = "127.0.0.1"   # local-only; use 0.0.0.0 for external access
port = 8201

[security]
jwt_secret_key = "change-me-to-a-long-random-string"

[database]
# type = "sqlite" (default) | "postgres"
type = "sqlite"
path = "weave_note.db"
# postgres mode uses these fields:
# host = "127.0.0.1"
# port = 5432
# username = "postgres"
# password = ""
# name = "weave_note"
```

Supported environment variables:

| Variable | Description |
|---|---|
| `PYTHON` | interpreter override (`start.sh` uses it first) |
| `HOST` / `PORT` | listen address/port override (`start.sh`) |
| `LOG_FILE` / `PID_FILE` | log/PID file paths (`start.sh`) |
| `JWT_SECRET_KEY` | JWT secret (used when not set in config.toml) |
| `CONFIG_MODEL_PATH` | config_model.toml path (defaults to config.toml's directory) |

### 4. Start

```bash
# run from the project root
chmod +x scripts/*.sh
bash scripts/start.sh
```

Defaults written: PID `weave-note/weave-note.pid`, log `weave-note/weave-note.log`.
Override via `LOG_FILE`, `PID_FILE`, `HOST`, `PORT`, `PYTHON`.

### 5. Verify

```bash
# health check
curl http://127.0.0.1:8201/healthz
# expect: {"status":"ok","service":"weave-note","database":"ok"}

# login (test / 123456 auto-created on first launch)
curl -sS -X POST http://127.0.0.1:8201/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"123456"}'

# frontend
open http://127.0.0.1:8201/
```

Log in with `test / 123456` in the browser: create notebooks, create/edit/delete notes, search.

#### 5.1 End-to-end acceptance walkthrough

1. Open `http://127.0.0.1:8201/`, log in with `test / 123456`
2. Click「＋」to create a notebook, name it, confirm
3. Click「＋ 新建」, enter title and body, click「保存」
4. Type a body keyword into the search box, press Enter, confirm the note is hit
5. Re-open the note, edit the body, save again
6. Confirm the change persists and survives a service restart

### 6. Stop

```bash
bash scripts/stop.sh
```

## Core API

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | register (body: username/password) |
| POST | `/api/auth/login` | login, returns JWT |
| POST | `/api/auth/logout` | logout |
| GET | `/api/auth/me` | current user |
| GET | `/api/notes/notebooks` | list notebooks |
| POST | `/api/notes/notebooks` | create notebook |
| PUT | `/api/notes/notebooks/{id}` | rename notebook |
| PUT | `/api/notes/notebooks/{id}/default` | set default notebook |
| GET | `/api/notes/default-notebook` | get default notebook |
| DELETE | `/api/notes/notebooks/{id}` | delete notebook (default cannot be deleted) |
| POST | `/api/notes/notebooks/bulk-delete` | bulk-delete notebooks |
| POST | `/api/notes/notebooks/bulk-export` | bulk-export notebooks (zip) |
| GET | `/api/notes/notebooks/{id}/export` | export notebook CSV |
| GET | `/api/notes/notebooks/{id}/notes` | list notes |
| POST | `/api/notes/notebooks/{id}/notes` | create note |
| GET | `/api/notes/notes/{id}` | note detail |
| PUT | `/api/notes/notes/{id}` | save note |
| DELETE | `/api/notes/notes/{id}` | delete note |
| PUT | `/api/notes/notes/{id}/move` | move note |
| POST | `/api/notes/notes/bulk-delete` | bulk-delete notes |
| POST | `/api/notes/notes/bulk-move` | bulk-move notes |
| POST | `/api/notes/notes/bulk-export` | bulk-export notes (zip) |
| POST | `/api/notes/quick` | quick note |
| GET | `/api/notes/search?q=keyword` | full-text search |
| GET | `/api/notes/notes/{id}/export?format=md` | export note |
| GET/POST | `/api/export-tasks[/{task_id}]` | async export tasks: create/query/download/cancel/delete |
| POST | `/api/files/upload` | file upload & parse (docx/pptx/xlsx/pdf/image) |
| POST | `/api/images/upload` `/upload-media` | image upload |
| GET | `/api/images/serve` | image serving |

All endpoints except register/login/healthz require:

```http
Authorization: Bearer <access_token>
```

## FAQ

### Startup failure: database connection error

SQLite mode (default): ensure `backend/` is writable (creates `weave_note.db` on first launch); the log line `Weave Note 启动完成` means all is well.

PostgreSQL mode: confirm PostgreSQL is up and the database exists:

```bash
pg_isready -h 127.0.0.1 -p 5432
psql -U postgres -h 127.0.0.1 -d weave_note -c 'SELECT 1'
```

### Port in use

Change `port` in `backend/config.toml`, or override at startup:

```bash
PORT=8204 bash scripts/start.sh
```

### Forgot the test account password

Delete the test user in `weave_note.db` (SQLite, default) or the `weave_note` DB (PostgreSQL) and restart — it auto-recreates. Better: register a new account via the register API.

### Where are the logs?

Default: `weave-note/weave-note.log`; or the path set via the `LOG_FILE` environment variable.
