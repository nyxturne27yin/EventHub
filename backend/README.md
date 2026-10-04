# EventHub Backend

The backend is a FastAPI application. Its current endpoint is a health check.

## Current Status

Implemented: `GET /health`

The app checks its PostgreSQL connection during startup by running `SELECT 1` through SQLAlchemy.

Not yet implemented: event and user APIs, authentication, database tables, or event/user data persistence.

## Setup

Run these commands from the repository root in PowerShell. Activate the project’s `.venv` first if the terminal prompt does not show `(.venv)`.

Install the backend dependencies:

```powershell
python -m pip install -r backend\requirements.txt

```

## Start the Development Server

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

## Local URLs

- Health check: `http://127.0.0.1:8000/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Alternative API docs: `http://127.0.0.1:8000/redoc`


## Local PostgreSQL Setup

The local development database uses PostgreSQL with these settings:

- Host: `127.0.0.1`
- Port: `5432`
- Database: `eventhub`
- Login role: `eventhub_app`

Copy the root `.env.example` file to `.env` and set the local database password in `.env`. The `.env` file is ignored by Git and must not be committed.



## Render Web Service Setup

Configure a Python web service for the EventHub backend with:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- CORS origins: set `CORS_ORIGINS` in Render to the exact frontend origin or comma-separated origins allowed to call the API from a browser. The local defaults are `http://localhost:5500` and `http://127.0.0.1:5500`.

Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in the Render service environment. Use the values from the Render PostgreSQL database, not the local `.env` values. Keep the production password in Render; never commit it to GitHub.
