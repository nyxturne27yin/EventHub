# EventHub Backend

The backend is a FastAPI application. Its current endpoint is a health check.

## Current Status

Implemented: `GET /health`

Not yet implemented: event and user APIs, authentication, and database connection.

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